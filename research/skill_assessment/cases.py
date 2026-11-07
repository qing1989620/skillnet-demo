"""Three D1-only case operationalizations, not independent human gold."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .boundary import Clause, Contract, preflight
from .evidence import Bundle
from .static_checks import inspect_package

PILOT_NAMES = (
    "gh-claude-data-quality-auditor-9d8e63",
    "gh-agentic-weather-data-lifecycle-management-340ae1",
    "gh-agentic-solidity-security-264697",
)


def contract_and_scenarios(bundle: Bundle) -> tuple[Contract, list[dict]]:
    cite = bundle.cite
    scenarios: list[dict[str, Any]]
    if bundle.name == PILOT_NAMES[0]:
        contract = Contract(
            "bundled_csv_profiler_workflow",
            ("csv_dataset_audit",),
            ("database_schema_design", "etl_pipeline_implementation", "financial_model_validation"),
            (
                Clause(
                    "input_format",
                    "csv",
                    "仅刻画附带 CSV 脚本，不把它扩张为所有数据格式。",
                    "reviewer_operationalization",
                    (cite("scripts/data_profiler.py", 22, 27),),
                ),
                Clause(
                    "read_authorized",
                    True,
                    "执行前由任务适配器确认输入读取权限。",
                    "reviewer_operationalization",
                    (cite("SKILL.md", 50, 61),),
                ),
            ),
            (
                Clause(
                    "auto_fix_assumed",
                    True,
                    "未确认假设不能自动修复。",
                    "source_declared",
                    (cite("SKILL.md", 179, 185),),
                ),
            ),
            "这只是 CSV 配套模块的操作契约；整个 Skill 的开放式咨询范围不能由它穷尽。",
            (cite("SKILL.md", 12, 19), cite("SKILL.md", 210, 213)),
        )
        scenarios = [
            {
                "id": "csv-normal",
                "task": "csv_dataset_audit",
                "facts": {"input_format": "csv", "read_authorized": True, "auto_fix_assumed": False},
            },
            {
                "id": "csv-excel-not-established",
                "task": "csv_dataset_audit",
                "facts": {"input_format": "xlsx", "read_authorized": True, "auto_fix_assumed": False},
            },
            {
                "id": "csv-read-permission-unknown",
                "task": "csv_dataset_audit",
                "facts": {"input_format": "csv", "auto_fix_assumed": False},
            },
            {
                "id": "csv-financial-model-excluded",
                "task": "financial_model_validation",
                "facts": {"input_format": "csv", "read_authorized": True, "auto_fix_assumed": False},
            },
            {
                "id": "csv-unconfirmed-auto-fix",
                "task": "csv_dataset_audit",
                "facts": {"input_format": "csv", "read_authorized": True, "auto_fix_assumed": True},
            },
        ]
    elif bundle.name == PILOT_NAMES[1]:
        contract = Contract(
            "weather_file_lifecycle",
            ("weather_file_lifecycle",),
            ("weather_forecast_accuracy", "scientific_decoder_validation", "cache_eviction_policy_design"),
            (
                Clause(
                    "ownership_known",
                    True,
                    "必须先确认路径归属。",
                    "source_declared",
                    (cite("SKILL.md", 35, 47),),
                ),
                Clause(
                    "consumers_closed",
                    True,
                    "交互数据要等最后一个消费者关闭后释放。",
                    "source_declared",
                    (cite("SKILL.md", 79, 92),),
                ),
            ),
            (
                Clause(
                    "request_deletes_shared_cache",
                    True,
                    "请求清理不能删除共享缓存根。",
                    "source_declared",
                    (cite("SKILL.md", 107, 115),),
                ),
                Clause(
                    "request_deletes_user_export",
                    True,
                    "用户导出不属于请求自动清理范围。",
                    "source_declared",
                    (cite("SKILL.md", 39, 45),),
                ),
                Clause(
                    "unsafe_target",
                    True,
                    "归并表示根目录、越界及符号链接逃逸等禁止目标。",
                    "reviewer_operationalization",
                    (cite("SKILL.md", 128, 137),),
                ),
            ),
            "只检查删除/释放阶段。运行中的正常读取不要求 consumers_closed；多进程租约仍需额外设计。",
            (cite("SKILL.md", 18, 24), cite("SKILL.md", 152, 159)),
        )
        normal = {
            "ownership_known": True,
            "consumers_closed": True,
            "request_deletes_shared_cache": False,
            "request_deletes_user_export": False,
            "unsafe_target": False,
        }
        scenarios = [
            {"id": "weather-close-owned-session", "task": "weather_file_lifecycle", "facts": normal},
            {
                "id": "weather-view-still-open",
                "task": "weather_file_lifecycle",
                "facts": {**normal, "consumers_closed": False},
            },
            {
                "id": "weather-owner-unknown",
                "task": "weather_file_lifecycle",
                "facts": {**normal, "ownership_known": None},
            },
            {
                "id": "weather-delete-cache",
                "task": "weather_file_lifecycle",
                "facts": {**normal, "request_deletes_shared_cache": True},
            },
            {
                "id": "weather-delete-export",
                "task": "weather_file_lifecycle",
                "facts": {**normal, "request_deletes_user_export": True},
            },
            {"id": "weather-forecast-excluded", "task": "weather_forecast_accuracy", "facts": normal},
            {
                "id": "weather-unsafe-path",
                "task": "weather_file_lifecycle",
                "facts": {**normal, "unsafe_target": True},
            },
        ]
    else:
        contract = Contract(
            "solidity_security_advice",
            ("solidity_security_review_advice",),
            ("environment_independent_security_certificate",),
            (
                Clause(
                    "contract_and_environment_known",
                    True,
                    "没有具体环境、权限、输入和成功标准时先澄清。",
                    "source_declared",
                    (cite("SKILL.md", 39, 42),),
                ),
            ),
            (),
            "包含安全模式与审计准备建议。环境无关安全证书被排除，是对声明限制的审查员操作化；不判为恶意。",
            (cite("SKILL.md", 13, 26), cite("SKILL.md", 39, 42)),
        )
        scenarios = [
            {
                "id": "solidity-advice",
                "task": "solidity_security_review_advice",
                "facts": {"contract_and_environment_known": True},
            },
            {"id": "solidity-environment-missing", "task": "solidity_security_review_advice", "facts": {}},
            {
                "id": "solidity-certificate",
                "task": "environment_independent_security_certificate",
                "facts": {"contract_and_environment_known": True},
            },
            {"id": "solidity-unlisted-task", "task": "unlisted_task", "facts": {}},
        ]
    for clause in contract.required + contract.prohibited:
        for evidence in clause.evidence:
            bundle.verify(evidence)
    for evidence in contract.scope_evidence:
        bundle.verify(evidence)
    return contract, [
        {
            **s,
            "scenario_kind": "reviewer_authored_preflight_example_not_skill_execution",
            "result": preflight(contract, s["task"], s["facts"]),
        }
        for s in scenarios
    ]


def build_case(bundle: Bundle, legacy: dict) -> dict:
    contract, scenarios = contract_and_scenarios(bundle)
    if bundle.name == PILOT_NAMES[0]:
        review = {
            "conclusion": "DQS 的唯一性和时效性分量是脚本常数默认值，不能单凭该分数确认真实测量。",
            "qualification": "主文档也称脚本分数基于完整性/一致性信号；整个工作流可能另行补测，未判整个 Skill 无用。",
            "evidence": [
                asdict(bundle.cite("SKILL.md", 110, 125)),
                asdict(bundle.cite("SKILL.md", 41, 47)),
                asdict(bundle.cite("scripts/data_profiler.py", 116, 120)),
            ],
        }
    elif bundle.name == PILOT_NAMES[1]:
        review = {
            "conclusion": "文档能支持明确的归属、释放时点和禁止清理对象，适合操作化边界预检。",
            "qualification": "这是文档层面的正向证据；未测试运行时文件生命周期，未验证天气预测质量。",
            "evidence": [asdict(c) for c in contract.scope_evidence],
        }
    else:
        review = {
            "conclusion": "完整 playbook 提供建议和反例，但资源列表的八个本地文件未随登记包提供。",
            "qualification": "需核查它们是否为必要资源或可选阅读；不据此把教学漏洞示例判为恶意。",
            "evidence": [asdict(bundle.cite("resources/implementation-playbook.md", 497, 506))],
        }
    return {
        "skill_uid": bundle.skill_uid,
        "name": bundle.name,
        "review_kind": "current_agent_static_case_review_not_human_gold",
        "source_repo": bundle.source_repo,
        "source_commit": bundle.source_commit,
        "source_path": bundle.source_path,
        "source_files": [
            {"path": f.path, "sha256": f.sha256, "lines": len(f.text.splitlines())}
            for f in bundle.files.values()
        ],
        "static_checks": inspect_package(bundle),
        "agent_review": review,
        "boundary_contract": asdict(contract),
        "preflight_scenarios": scenarios,
        "legacy_card_baseline": {
            k: legacy[k]
            for k in ("stored_quality", "stored_score", "recomputed_quality", "recomputed_score", "scope")
        },
        "ordinal_ratings": {
            dim: {"score": None, "status": "not_independently_rated"}
            for dim in (
                "contract_consistency",
                "completeness",
                "static_executability",
                "verification_quality",
                "maintainability",
                "provenance_license",
                "cost_awareness",
                "safety_documentation",
            )
        },
        "safety_and_license_gate": "human_review_required_not_certified",
        "empirical_capability": "not_tested",
        "task_conditional_utility": "not_measured",
        "citation_semantic_support": "requires_independent_review",
        "publication": "metadata_and_short_findings_only_no_raw_package_republication",
    }
