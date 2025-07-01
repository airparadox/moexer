import time
import logging
from functools import wraps
from typing import Dict, Any, Callable
from collections import defaultdict, deque
from datetime import datetime

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Класс для мониторинга производительности и метрик"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.counters = defaultdict(int)
        self.errors = defaultdict(int)
        self.execution_times = defaultdict(deque)
        self.max_history = 100  # Максимальное количество записей в истории
    
    def record_execution_time(self, service_name: str, execution_time: float):
        """Записывает время выполнения для сервиса"""
        self.execution_times[service_name].append({
            'time': execution_time,
            'timestamp': datetime.now()
        })
        
        # Ограничиваем размер истории
        if len(self.execution_times[service_name]) > self.max_history:
            self.execution_times[service_name].popleft()
    
    def increment_counter(self, service_name: str, status: str = 'success'):
        """Увеличивает счетчик для сервиса"""
        counter_key = f"{service_name}_{status}"
        self.counters[counter_key] += 1
    
    def record_error(self, service_name: str, error_type: str):
        """Записывает ошибку для сервиса"""
        error_key = f"{service_name}_{error_type}"
        self.errors[error_key] += 1
    
    def get_average_execution_time(self, service_name: str) -> float:
        """Возвращает среднее время выполнения для сервиса"""
        if service_name not in self.execution_times:
            return 0.0
        
        times = [record['time'] for record in self.execution_times[service_name]]
        return sum(times) / len(times) if times else 0.0
    
    def get_success_rate(self, service_name: str) -> float:
        """Возвращает процент успешных вызовов для сервиса"""
        success_key = f"{service_name}_success"
        error_key = f"{service_name}_error"
        
        total_calls = self.counters[success_key] + self.counters[error_key]
        if total_calls == 0:
            return 0.0
        
        return (self.counters[success_key] / total_calls) * 100
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Возвращает сводку по всем метрикам"""
        summary = {
            'services': {},
            'total_calls': sum(self.counters.values()),
            'total_errors': sum(self.errors.values())
        }
        
        # Собираем метрики по сервисам
        services = set()
        for key in self.counters.keys():
            service = key.rsplit('_', 1)[0]
            services.add(service)
        
        for service in services:
            summary['services'][service] = {
                'average_execution_time': self.get_average_execution_time(service),
                'success_rate': self.get_success_rate(service),
                'total_calls': self.counters.get(f"{service}_success", 0) + self.counters.get(f"{service}_error", 0)
            }
        
        return summary

# Глобальный экземпляр монитора
performance_monitor = PerformanceMonitor()

def monitor_performance(service_name: str):
    """Декоратор для мониторинга производительности функций"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Записываем успешное выполнение
                performance_monitor.record_execution_time(service_name, execution_time)
                performance_monitor.increment_counter(service_name, 'success')
                
                logger.debug(f"{service_name}: executed in {execution_time:.3f}s")
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                # Записываем ошибку
                performance_monitor.record_execution_time(service_name, execution_time)
                performance_monitor.increment_counter(service_name, 'error')
                performance_monitor.record_error(service_name, type(e).__name__)
                
                logger.error(f"{service_name}: failed after {execution_time:.3f}s with {type(e).__name__}: {e}")
                raise
        return wrapper
    return decorator

def get_performance_report() -> str:
    """Возвращает отчет о производительности в текстовом формате"""
    summary = performance_monitor.get_metrics_summary()
    
    report = [
        "=== ОТЧЕТ О ПРОИЗВОДИТЕЛЬНОСТИ ===",
        f"Общее количество вызовов: {summary['total_calls']}",
        f"Общее количество ошибок: {summary['total_errors']}",
        ""
    ]
    
    for service_name, metrics in summary['services'].items():
        report.extend([
            f"Сервис: {service_name}",
            f"  Среднее время выполнения: {metrics['average_execution_time']:.3f}с",
            f"  Процент успешных вызовов: {metrics['success_rate']:.1f}%",
            f"  Общее количество вызовов: {metrics['total_calls']}",
            ""
        ])
    
    return "\n".join(report)

def log_performance_summary():
    """Выводит сводку производительности в лог"""
    logger.info(get_performance_report())