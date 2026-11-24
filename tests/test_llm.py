import pytest

from study_abroad.llm import MissingAPIKeyError, load_deepseek_chat_model


def test_loads_deepseek_settings_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://example.test")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")

    model = load_deepseek_chat_model()

    assert model.model_name == "deepseek-reasoner"
    assert str(model.openai_api_base) == "https://example.test"
    assert model.openai_api_key.get_secret_value() == "test-key"
    assert model.request_timeout == 60.0


def test_missing_key_raises(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(MissingAPIKeyError):
        load_deepseek_chat_model()
