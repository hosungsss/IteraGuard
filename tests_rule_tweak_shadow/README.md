# Rule Tweak Shadow tests

Only synthetic/fixture and existing offline unit contracts. The new observer is a *diagnostic* and must not change execution. Run:
python -m unittest discover -s tests_rule_tweak_shadow -v

Current GitHub CI also runs the historic Arena v5.6/v5.4/v5.1 suites, Rulebook tests and Node UI tests. Those pass/fail results must be checked on the exact merged commit. No physical Zoro checkpoint authentication, Android, NPU, live banking or independent label evaluation is performed here.
