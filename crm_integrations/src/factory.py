"""
Factory для создания CRM адаптеров
"""

from typing import Optional, Dict, Any
from enum import Enum

from .base import BaseCRMAdapter


class CRMType(str, Enum):
    """Поддерживаемые типы CRM"""
    YCLIENTS = "yclients"
    DIKIDI = "dikidi"
    BITRIX24 = "bitrix24"
    ONEC = "1c"
    AMOCRM = "amocrm"
    ALTEGIO = "altegio"
    EASYWEEK = "easyweek"


class CRMFactory:
    """
    Factory для создания CRM адаптеров
    
    Usage:
        adapter = CRMFactory.create(
            crm_type=CRMType.YCLIENTS,
            api_key="your_key",
            company_id="123"
        )
    """
    
    _adapters: Dict[CRMType, type] = {}
    
    @classmethod
    def register(cls, crm_type: CRMType, adapter_class: type):
        """
        Регистрация нового адаптера
        
        Args:
            crm_type: Тип CRM
            adapter_class: Класс адаптера
        """
        if not issubclass(adapter_class, BaseCRMAdapter):
            raise ValueError(f"{adapter_class} должен наследовать BaseCRMAdapter")
        
        cls._adapters[crm_type] = adapter_class
    
    @classmethod
    def create(
        cls,
        crm_type: CRMType,
        api_key: str,
        base_url: Optional[str] = None,
        **kwargs
    ) -> BaseCRMAdapter:
        """
        Создание CRM адаптера
        
        Args:
            crm_type: Тип CRM
            api_key: API ключ
            base_url: Базовый URL (если требуется)
            **kwargs: Дополнительные параметры
            
        Returns:
            Экземпляр CRM адаптера
            
        Raises:
            ValueError: Если CRM тип не зарегистрирован
        """
        adapter_class = cls._adapters.get(crm_type)
        
        if not adapter_class:
            raise ValueError(
                f"CRM тип '{crm_type}' не зарегистрирован. "
                f"Доступные: {list(cls._adapters.keys())}"
            )
        
        return adapter_class(api_key=api_key, base_url=base_url, **kwargs)
    
    @classmethod
    def get_available_crm_types(cls) -> list[CRMType]:
        """
        Получить список доступных CRM типов
        
        Returns:
            Список зарегистрированных CRM типов
        """
        return list(cls._adapters.keys())


# Автоматическая регистрация адаптеров при импорте
def _auto_register_adapters():
    """Автоматическая регистрация всех доступных адаптеров"""
    try:
        from .adapters.yclients import YClientsAdapter
        CRMFactory.register(CRMType.YCLIENTS, YClientsAdapter)
    except ImportError:
        pass
    
    try:
        from .adapters.dikidi import DikidiAdapter
        CRMFactory.register(CRMType.DIKIDI, DikidiAdapter)
    except ImportError:
        pass
    
    try:
        from .adapters.bitrix24 import Bitrix24Adapter
        CRMFactory.register(CRMType.BITRIX24, Bitrix24Adapter)
    except ImportError:
        pass
    
    try:
        from .adapters.onec import OneCAdapter
        CRMFactory.register(CRMType.ONEC, OneCAdapter)
    except ImportError:
        pass

    try:
        from .adapters.amocrm import AmoCRMAdapter
        CRMFactory.register(CRMType.AMOCRM, AmoCRMAdapter)
    except ImportError:
        pass

    try:
        from .adapters.altegio import AltegioAdapter
        CRMFactory.register(CRMType.ALTEGIO, AltegioAdapter)
    except ImportError:
        pass

    try:
        from .adapters.easyweek import EasyWeekAdapter
        CRMFactory.register(CRMType.EASYWEEK, EasyWeekAdapter)
    except ImportError:
        pass


# Регистрируем адаптеры при импорте модуля
_auto_register_adapters()
