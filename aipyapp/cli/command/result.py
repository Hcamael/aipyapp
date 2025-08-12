#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any
from pydantic import BaseModel, model_validator


class CommandResult(BaseModel):
    command: str
    subcommand: str | None
    args: dict[str, Any]
    result: Any 

class TaskModeResult(BaseModel):
    task: Any | None = None
    instruction: str | None = None
    title: str | None = None

    @model_validator(mode='after')
    def validate_task_or_instruction(self):
        if self.task is None and self.instruction is None:
            raise ValueError("task or instruction must be provided")
        return self
    

