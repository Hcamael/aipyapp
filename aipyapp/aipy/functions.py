import inspect
from typing import Any, Callable, Dict, Optional, List

from loguru import logger
from pydantic import create_model, ValidationError


class FunctionError(Exception):
    """Base exception for function calls"""
    pass

class FunctionNotFoundError(FunctionError):
    """Function/method not found exception"""
    pass

class ParameterValidationError(FunctionError):
    """Parameter validation exception"""
    pass

class FunctionManager:
    """Function manager - manage all callable functions"""
    
    def __init__(self):
        """Initialize function manager"""
        self.function_registry: Dict[str, Dict[str, Any]] = {}
        self.logger = logger.bind(src=self.__class__.__name__)
    
    def register_function(self, func: Callable, name: str = None) -> bool:
        """Register function
        
        Args:
            func: Function to register
            name: Custom function name, default is the function name
            
        Returns:
            Whether the function is registered successfully
        """
        func_name = name or func.__name__
        sig = inspect.signature(func)
        
        fields = {}
        for param_name, param in sig.parameters.items():
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else Any
            default = param.default if param.default != inspect.Parameter.empty else ...
            fields[param_name] = (annotation, default)
        
        ParamModel = create_model(f"{func_name}_Params", **fields)
        
        self.function_registry[func_name] = {
            "func": func,
            "signature": str(sig),
            "doc": inspect.getdoc(func) or "",
            "param_model": ParamModel
        }
        
        self.logger.debug(f"Registered function: {func_name}")
        return True

    def register_functions(self, functions: Dict[str, Callable]) -> int:
        """Batch register object instance methods
        
        Args:
            functions: Function name list
        """
        success_count = 0
        for func_name, func in functions.items():
            if self.register_function(func, func_name):
                success_count += 1
        self.logger.info(f"Registered {success_count}/{len(functions)} functions")
        return success_count

    def call(self, func_name: str, **kwargs) -> Any:
        """Call the registered function

        Args:
            func_name: Function name
            **kwargs: Function parameters
            
        Returns:
            Function execution result
            
        Raises:
            FunctionNotFoundError: Function not found
            ParameterValidationError: Parameter validation failed
        """
        entry = self.function_registry.get(func_name)
        if not entry:
            self.logger.error(f"Function '{func_name}' not found")
            raise FunctionNotFoundError(f"Function '{func_name}' not found")
        
        fn = entry["func"]
        ParamModel = entry.get("param_model")
        
        try:
            parsed = ParamModel(**kwargs)
            self.logger.info(f"Calling function {func_name}, parameters: {parsed.model_dump()}")
            result = fn(**parsed.model_dump())
            return result
        
        except ValidationError as e:
            self.logger.error(f"Function '{func_name}' parameter validation failed: {e}")
            raise ParameterValidationError(f"Parameter validation failed: {e}")
        except Exception as e:
            self.logger.error(f"Function '{func_name}' execution failed: {e}")
            raise
    
    def get_functions(self) -> Dict[str, Dict[str, str]]:
        """Get all functions
        
        Returns:
            All functions
        """
        functions = {}
        for name, meta in self.function_registry.items():
            functions[name] = {
                "signature": meta["signature"],
                "docstring": meta["doc"],
            }
        return functions
    
    def unregister_function(self, func_name: str) -> bool:
        """Unregister function
        
        Args:
            func_name: Function name
            
        Returns:
            Whether the function is unregistered successfully
        """
        if func_name in self.function_registry:
            del self.function_registry[func_name]
            self.logger.debug(f"Unregistered function: {func_name}")
            return True
        return False
    
    def clear_registry(self, group: Optional[str] = None):
        """Clear the registry
        
        Args:
            group: Specify the group, None means clear all
        """
        if group is None:
            self.function_registry.clear()
            self.logger.info("Cleared all registered functions")
        else:
            to_remove = [
                name for name, meta in self.function_registry.items()
                if meta["group"] == group
            ]
            for name in to_remove:
                del self.function_registry[name]
            self.logger.info(f"Cleared functions in group {group}")
    
    def get_registry(self) -> Dict[str, Dict[str, Any]]:
        """Get the complete registry (read-only)
        
        Returns:
            Copy of the registry
        """
        return self.function_registry.copy()
