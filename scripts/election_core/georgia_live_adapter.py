from .generated_scope_adapter import GeneratedScopeStateAdapter


class GeorgiaLiveAdapter(GeneratedScopeStateAdapter):
    expected_state = "GA"
    authority = "Georgia Secretary of State"
    system = "Election Night Reporting"
