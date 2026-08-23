from .generated_scope_adapter import GeneratedScopeStateAdapter


class MississippiLiveAdapter(GeneratedScopeStateAdapter):
    expected_state = "MS"
    authority = "Mississippi Secretary of State"
    system = "Statewide Election Management System / county provisional feeds"
