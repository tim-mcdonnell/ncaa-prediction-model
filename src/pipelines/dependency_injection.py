"""
Dependency Injection

This module provides dependency injection capabilities for the pipeline framework.
"""

import inspect
import logging
from functools import wraps
from typing import Any, Callable, Dict, Type, TypeVar, get_type_hints

# Set up logging
logger = logging.getLogger(__name__)

# Type variable for dependency types
T = TypeVar('T')


class Dependency:
    """
    Global registry and resolver for dependencies.
    
    This class provides static methods to register, resolve, and clear
    dependencies for dependency injection.
    """
    
    # Global registry of dependencies
    _registry: Dict[Type, Any] = {}
    
    @classmethod
    def register(cls, interface: Type[T], implementation: T) -> None:
        """
        Register an implementation for an interface.
        
        Args:
            interface: The interface or protocol type
            implementation: The concrete implementation
        """
        cls._registry[interface] = implementation
        logger.debug(f"Registered dependency for {interface.__name__}")
    
    @classmethod
    def resolve(cls, interface: Type[T]) -> T:
        """
        Resolve an implementation for an interface.
        
        Args:
            interface: The interface or protocol type
            
        Returns:
            The registered implementation
            
        Raises:
            KeyError: If no implementation is registered for the interface
        """
        if interface not in cls._registry:
            raise KeyError(f"No dependency registered for {interface.__name__}")
            
        return cls._registry[interface]
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered dependencies."""
        cls._registry.clear()
        logger.debug("Cleared dependency registry")


def injectable(init: Callable) -> Callable:
    """
    Decorator for injectable constructor methods.
    
    This decorator allows constructor parameters to be automatically
    injected from the dependency registry if not explicitly provided.
    
    Args:
        init: The constructor method to decorate
        
    Returns:
        Decorated constructor that handles dependency injection
    """
    @wraps(init)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        # Get parameter types from type hints
        param_types = get_type_hints(init)
        
        # Remove return type if present
        if 'return' in param_types:
            del param_types['return']
        
        # Get parameter names and defaults
        signature = inspect.signature(init)
        parameters = signature.parameters
        
        # Skip self parameter
        param_names = list(parameters.keys())[1:]  # Skip 'self'
        
        # Check for missing params that need to be injected
        for name in param_names:
            # Skip if explicitly provided in args or kwargs
            if name in kwargs or len(args) > param_names.index(name):
                continue
                
            # Skip if parameter has a default value
            param = parameters[name]
            if param.default is not param.empty:
                continue
                
            # Try to inject from registry
            if name in param_types:
                dependency_type = param_types[name]
                try:
                    # Resolve dependency from registry
                    dependency = Dependency.resolve(dependency_type)
                    kwargs[name] = dependency
                    dep_name = dependency_type.__name__
                    class_name = self.__class__.__name__
                    logger.debug(f"Injected {dep_name} into {class_name}")
                except KeyError:
                    # If not in registry, let normal init handling raise 
                    # the appropriate error
                    dep_name = dependency_type.__name__
                    class_name = self.__class__.__name__
                    logger.warning(
                        f"No dependency found for {dep_name} in {class_name}"
                    )
        
        # Call original init with resolved dependencies
        return init(self, *args, **kwargs)
    
    return wrapper 