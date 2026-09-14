# Controlling Source Specifications

This build was implemented against the two user-provided architecture specifications reviewed in full during the build session:

1. `NFL_2026_AITA_OPPORTUNITY_PROP_PIPELINE_BUILD_SPEC(1).md`
2. `NFL_2026_PYTHON_VS_TRADING_AGENT_BOUNDARY_SPEC(1).md`

The first controls the opportunity-first NFL model architecture, V1 market scope, data providers, quota policy, Monte Carlo, pricing, boards, and handoff contents.

The second controls the permanent production boundary: Python owns Dataset A and stops at the immutable handoff ZIP; the separate Claude NFL Trading Agent owns Dataset B, execution, close, grading, CLV, and trading audit.
