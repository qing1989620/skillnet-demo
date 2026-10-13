"""Real single-host external worker smoke test, isolated from the demo library.

Calls the configured model once through a bounded run. Uses public test data.
Starts its own API/worker children and stops only those children in finally.
"""
from pathlib import Path
import json
import os
import secrets
import subprocess
import sys
import time
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from skillnet.s1_identity import S1Auth,S1Context


def main():
    directory=ROOT/'.audit-tmp-upgrade'/('deployment-smoke-'+str(int(time.time())))
    directory.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONUTF8='1',SKILLNET_ENCODER='lexical',SKILLNET_WORKER_MODE='external',
             SKILLNET_S1_SIGNING_KEY=secrets.token_hex(32),SKILLNET_TOKEN='',
             SKILLNET_OUT_DIR=str(directory/'out'),SKILLNET_DATA_DIR=str(directory/'data'))
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    api=None;worker=None;logs=[]
    def start_api():
        log=(directory/'api.log').open('a',encoding='utf-8');logs.append(log)
        proc=subprocess.Popen([sys.executable,'-m','uvicorn','server:app','--host','127.0.0.1','--port','8849'],
                              cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
        for _ in range(120):
            if proc.poll() is not None:raise RuntimeError('Isolated API exited; inspect API log')
            try:
                if httpx.get('http://127.0.0.1:8849/api/health',timeout=1).status_code==200:return proc
            except httpx.HTTPError:pass
            time.sleep(.25)
        proc.terminate();raise RuntimeError('Isolated API startup timeout')
    def stop(proc):
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
    try:
        api=start_api()
        context=S1Context('smoke-tenant','smoke-user','smoke-project')
        with httpx.Client(base_url='http://127.0.0.1:8849',auth=S1Auth(context,env['SKILLNET_S1_SIGNING_KEY']),timeout=20) as client:
            cancelled=client.post('/api/runs',json={'task':'队列取消测试，禁止执行','max_steps':1}).raise_for_status().json()['run_id']
            client.post(f'/api/runs/{cancelled}/cancel').raise_for_status()
            cancel_record=client.get(f'/api/runs/{cancelled}').raise_for_status().json()
            assert cancel_record['status']=='CANCELLED' and cancel_record['llm_calls']==0
            result=client.post('/api/runs',json={'task':'公开模拟测试：只用 Python 标准库，生成 measurements.csv，列名 value，值为 2、3、5；打印合计 10 并标明模拟数据。只规划和执行一步。','max_steps':1,'max_cost_yuan':.6,'max_seconds':240,'max_llm_calls':20}).raise_for_status().json()
            rid=result['run_id'];assert result['queued']
            stop(api);api=start_api()  # Queued job survives API process replacement.
            queued=client.get('/api/runs/'+rid).raise_for_status().json();assert queued['status']=='CREATED'
            log=(directory/'worker.log').open('a',encoding='utf-8');logs.append(log)
            worker=subprocess.Popen([sys.executable,'-m','skillnet.worker'],cwd=ROOT,env=env,
                                    stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
            deadline=time.monotonic()+280;last='';restarted=False
            while time.monotonic()<deadline:
                run=client.get('/api/runs/'+rid).raise_for_status().json()
                if run['status']!=last:print('Worker:',run['status'],flush=True);last=run['status']
                if run['status'] in ('EXECUTING','VERIFYING') and not restarted:
                    stop(api);api=start_api();restarted=True
                if run['status'] in ('COMPLETED','PARTIAL','FAILED','BUDGET_EXCEEDED','CANCELLED','INTERRUPTED'):break
                if worker.poll() is not None:raise RuntimeError('External worker stopped unexpectedly')
                time.sleep(1)
            assert run['status']=='COMPLETED',run.get('error')
            assert run['artifacts']
            path='/api/runs/'+rid+'/artifacts/'+run['artifacts'][0]['name']
            assert client.get(path).status_code==200
            with httpx.Client(base_url=client.base_url,auth=S1Auth(S1Context('smoke-tenant','other','smoke-project'),env['SKILLNET_S1_SIGNING_KEY'])) as foreign:
                assert foreign.get('/api/runs/'+rid).status_code==404
                assert foreign.get(path).status_code==404
                assert foreign.get('/api/runs').json()['total']==0
            events=client.get('/api/runs/'+rid+'/stream').raise_for_status().text
            assert 'run.finished' in events
            report=dict(status='passed',run_id=rid,queue_survived_api_restart=True,api_restarted_during_worker=restarted,
                        external_worker=True,cancelled_before_execution=True,tenant_run_and_artifact_isolation=True,
                        terminal_sse_replay=True,cost_yuan=run['cost_yuan'],acceptance=run.get('staged',{}).get('acceptance'),
                        boundary='single host, one writer, process execution; Docker runtime and target S1 not exercised')
            (ROOT/'out/deployment-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(report,ensure_ascii=False),flush=True)
    finally:
        stop(worker);stop(api)
        for log in logs:log.close()


if __name__=='__main__':main()
