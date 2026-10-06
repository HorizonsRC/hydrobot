"""This turns a 'provider: ...' line in the config into a Provider"""

from hydrobot.providers.horizons import HorizonsProvider, HorizonsProviderConfig


def build_provider(config):
    if config.provider == "horizons":
        provider_config = HorizonsProviderConfig(
            **config.provider_params
        )
        return HorizonsProvider(provider_config)

    raise ValueError(
        f"Unknown data provider: {config.provider}"
    )
