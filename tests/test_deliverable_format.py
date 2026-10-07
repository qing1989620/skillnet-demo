from skillnet.artifacts import generate_deliverables, safe_filename


def test_text_deliverables_cannot_masquerade_as_binary_files(monkeypatch):
    from skillnet import llm

    monkeypatch.setattr(llm, "chat_json", lambda *args, **kwargs: {
        "deliverables": [{"name": "barplot.png", "kind": "doc", "content": "图表绘制说明。" * 40}]
    })
    result = generate_deliverables("演示", {"artifacts": ["barplot.png"]}, [])
    file = result["files"][0]
    assert file["name"] == "barplot.md"
    assert file["declared_as"] == "barplot.png"
    assert file["bytes"] == len(file["body"].encode("utf-8"))


def test_filename_keeps_expected_format_after_sanitizing_and_truncation():
    assert safe_filename("../../图表.xlsx", "table") == "图表.csv"
    assert safe_filename("report.txt", "doc") == "report.txt"
    assert safe_filename("script.png", "code") == "script.py"
    assert safe_filename("analysis", "code") == "analysis.py"
    long_name = safe_filename("a" * 100 + ".py", "code")
    assert len(long_name) == 80
    assert long_name.endswith(".py")


def test_capability_proof_is_readonly_for_live_learning_statistics(monkeypatch):
    import server
    from skillnet.catalog import SkillLibrary
    from skillnet.schema import Skill

    library = SkillLibrary([
        Skill(name="sample-a", description="分析均值", domain="analysis"),
        Skill(name="sample-b", description="分析方差", domain="analysis"),
        Skill(name="sample-c", description="文档写作", domain="docs"),
    ])
    monkeypatch.setattr(server, "STATE", {"lib": library})
    before = [s.to_dict() for s in library]
    for _ in range(3):
        result = server.capabilities()
        assert result["library"]["skills"] == 3
        assert result["linucb"]["near_delta"] > 0
    assert [s.to_dict() for s in library] == before
    assert library.dirty is False
