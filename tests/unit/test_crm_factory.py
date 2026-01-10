"""
Unit tests for CRM Factory
"""

import pytest
from crm_integrations.src.factory import CRMFactory, CRMType


class TestCRMFactory:
    """Tests for CRM adapter factory"""

    def test_available_crm_types(self):
        """Test that all expected CRM types are registered"""
        available = CRMFactory.get_available_crm_types()

        # Should have at least the main CRM types
        assert CRMType.YCLIENTS in available
        assert CRMType.BITRIX24 in available
        assert CRMType.ONEC in available

    def test_create_yclients_adapter(self):
        """Test creation of YCLIENTS adapter"""
        adapter = CRMFactory.create(
            crm_type=CRMType.YCLIENTS,
            api_key="test_key",
            base_url="https://api.yclients.com"
        )

        assert adapter is not None
        assert adapter.get_crm_name() == "YClients"

    def test_create_bitrix24_adapter(self):
        """Test creation of Bitrix24 adapter"""
        adapter = CRMFactory.create(
            crm_type=CRMType.BITRIX24,
            api_key="test_key",
            base_url="https://test.bitrix24.ru"
        )

        assert adapter is not None
        assert adapter.get_crm_name() == "Bitrix24"

    def test_create_onec_adapter(self):
        """Test creation of 1C adapter"""
        adapter = CRMFactory.create(
            crm_type=CRMType.ONEC,
            api_key="test_key",
            base_url="https://1c-server.local"
        )

        assert adapter is not None
        assert "OneC" in adapter.get_crm_name() or "1C" in adapter.get_crm_name()

    def test_create_amocrm_adapter(self):
        """Test creation of amoCRM adapter"""
        adapter = CRMFactory.create(
            crm_type=CRMType.AMOCRM,
            api_key="test_key",
            base_url="https://company.amocrm.ru"
        )

        assert adapter is not None

    def test_invalid_crm_type_raises_error(self):
        """Test that invalid CRM type raises error"""
        with pytest.raises(ValueError, match="не зарегистрирован"):
            CRMFactory.create(
                crm_type="invalid_crm",
                api_key="test_key"
            )

    def test_adapters_have_required_methods(self):
        """Test that all adapters implement required interface"""
        for crm_type in CRMFactory.get_available_crm_types():
            adapter = CRMFactory.create(
                crm_type=crm_type,
                api_key="test_key",
                base_url="https://test.example.com"
            )

            # Check required methods exist
            assert hasattr(adapter, "get_client_by_phone")
            assert hasattr(adapter, "create_client")
            assert hasattr(adapter, "get_services")
            assert hasattr(adapter, "get_available_slots")
            assert hasattr(adapter, "create_appointment")
            assert hasattr(adapter, "health_check")

    def test_crm_type_enum_values(self):
        """Test CRM type enum has correct values"""
        assert CRMType.YCLIENTS.value == "yclients"
        assert CRMType.BITRIX24.value == "bitrix24"
        assert CRMType.ONEC.value == "1c"
        assert CRMType.AMOCRM.value == "amocrm"
        assert CRMType.DIKIDI.value == "dikidi"
        assert CRMType.ALTEGIO.value == "altegio"
        assert CRMType.EASYWEEK.value == "easyweek"
