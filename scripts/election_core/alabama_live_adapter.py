from .generated_scope_adapter import GeneratedScopeStateAdapter


class AlabamaLiveAdapter(GeneratedScopeStateAdapter):
    expected_state = "AL"
    authority = "Alabama Secretary of State"
    system = "AlabamaVotes Election Night Results"
