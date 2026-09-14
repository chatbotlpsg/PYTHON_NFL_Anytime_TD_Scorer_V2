from nfl_model.package.handoff import boundary_manifest


def test_boundary_is_locked():
    b = boundary_manifest()
    assert b["PIPELINE_BOUNDARY"]["PYTHON_COMPLETE_AT_ZIP"] is True
    assert b["POST_HANDOFF_OWNER"] == "CLAUDE_NFL_TRADING_AGENT"
    assert b["CLV"] == "NOT_PYTHON_RESPONSIBILITY"
    assert b["PLAY_GRADING"] == "NOT_PYTHON_RESPONSIBILITY"
