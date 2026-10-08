from skillnet import executor


def test_repair_prompt_keeps_failing_check_when_stderr_also_exists(tmp_path, monkeypatch):
    prompts=[]
    def chat(messages, **kwargs):
        prompts.append(messages[1]['content'])
        return '```python\nprint("validated")\n```'
    results=iter([
        {'ok':False,'stderr':'[failed] CSV verification','stdout':'mean dtype: False',
         'duration':.01,'artifacts':[],'error_kind':'exception'},
        {'ok':True,'stderr':'','stdout':'mean dtype: True; values verified',
         'duration':.01,'artifacts':[],'error_kind':''},
    ])
    monkeypatch.setattr(executor.sandbox,'available_stack',lambda:{})
    monkeypatch.setattr(executor.sandbox,'run_python',lambda *a,**k:next(results))
    monkeypatch.setattr(executor.llm,'chat',chat)
    monkeypatch.setattr(executor,'_record_execution',lambda *a,**k:{})
    result=executor.execute_step('public CSV example',{'action':'validate'},None,tmp_path,max_fix=1)
    assert result['final_ok'] and result['fixed'] and result['n_attempts']==2
    assert '[failed] CSV verification' in prompts[1]
    assert 'mean dtype: False' in prompts[1]
    assert '不得删除验收或硬编码通过' in prompts[1]


def test_long_diagnostics_fit_prompt_budget_without_losing_either_tail():
    message=executor._execution_diagnostic('e'*4000+'exception tail','o'*4000+'check False')
    assert len(message)<=executor.MAX_OUTPUT_IN_PROMPT
    assert 'exception tail' in message and 'check False' in message
    assert 'stderr 为空' in executor._execution_diagnostic('', 'specific failed check')
