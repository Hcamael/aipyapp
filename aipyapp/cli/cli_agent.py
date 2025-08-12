#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Dict, Any, Optional
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from loguru import logger

from .. import T, __version__
from ..aipy.agent_taskmgr import AgentTaskManager
from ..display import DisplayManager

# API 数据模型
class TaskRequest(BaseModel):
    instruction: str = Field(..., description="任务指令")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="任务元数据")

class TaskResponse(BaseModel):
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="响应消息")

class TaskStatusResponse(BaseModel):
    task_id: str
    instruction: str
    status: str
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    error: Optional[str]

class TaskResultResponse(BaseModel):
    task_id: str
    instruction: str
    status: str
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    error: Optional[str]
    output: Optional[Dict[str, Any]]

# 全局变量
agent_manager: Optional[AgentTaskManager] = None
app = FastAPI(
    title="AIPython Agent API",
    description="HTTP API for n8n integration with AIPython",
    version=__version__
)

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    logger.info("Starting AIPython Agent API server...")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理"""
    logger.info("Shutting down AIPython Agent API server...")
    if agent_manager and hasattr(agent_manager, 'executor'):
        agent_manager.executor.shutdown(wait=True)

@app.get("/", response_model=Dict[str, str])
async def root():
    """根路径 - API信息"""
    return {
        "name": "AIPython Agent API",
        "version": __version__,
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "submit_task": "POST /tasks",
            "get_task_status": "GET /tasks/{task_id}",
            "get_task_result": "GET /tasks/{task_id}/result",
            "list_tasks": "GET /tasks",
            "cancel_task": "DELETE /tasks/{task_id}",
            "health": "GET /health"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agent_manager": "initialized" if agent_manager else "not_initialized"
    }

@app.post("/tasks", response_model=TaskResponse)
async def submit_task(task_request: TaskRequest, background_tasks: BackgroundTasks):
    """提交新任务"""
    if not agent_manager:
        raise HTTPException(status_code=500, detail="Agent manager not initialized")
    
    try:
        # 提交任务
        task_id = await agent_manager.submit_task(
            instruction=task_request.instruction,
            metadata=task_request.metadata
        )
        
        # 在后台执行任务
        background_tasks.add_task(execute_task_background, task_id)
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message="Task submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to submit task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def execute_task_background(task_id: str):
    """后台执行任务"""
    try:
        await agent_manager.execute_task(task_id)
        logger.info(f"Task {task_id} completed")
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")

@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """获取任务状态"""
    if not agent_manager:
        raise HTTPException(status_code=500, detail="Agent manager not initialized")
    
    try:
        task_data = await agent_manager.get_task_status(task_id)
        return TaskStatusResponse(**task_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(task_id: str):
    """获取任务结果"""
    if not agent_manager:
        raise HTTPException(status_code=500, detail="Agent manager not initialized")
    
    try:
        result = await agent_manager.get_task_result(task_id)
        return TaskResultResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get task result: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks")
async def list_tasks():
    """列出所有任务"""
    if not agent_manager:
        raise HTTPException(status_code=500, detail="Agent manager not initialized")
    
    try:
        tasks = await agent_manager.list_tasks()
        return {"tasks": tasks}
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """取消任务"""
    if not agent_manager:
        raise HTTPException(status_code=500, detail="Agent manager not initialized")
    
    try:
        success = await agent_manager.cancel_task(task_id)
        if success:
            return {"message": f"Task {task_id} cancelled"}
        else:
            raise HTTPException(status_code=400, detail="Task cannot be cancelled")
    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/cleanup")
async def cleanup_tasks(max_age_hours: int = 24):
    """清理完成的任务"""
    if not agent_manager:
        raise HTTPException(status_code=500, detail="Agent manager not initialized")
    
    try:
        cleaned_count = agent_manager.cleanup_completed_tasks(max_age_hours)
        return {"message": f"Cleaned up {cleaned_count} tasks"}
    except Exception as e:
        logger.error(f"Failed to cleanup tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def init_agent_manager(settings):
    """初始化Agent管理器"""
    global agent_manager
    try:
        display_config = {'style': 'agent', 'quiet': True}
        display_manager = DisplayManager(display_config)
        agent_manager = AgentTaskManager(settings, display_manager=display_manager)
        logger.info("Agent manager initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize agent manager: {e}")
        return False

def main(settings):
    """Agent模式主函数"""
    global agent_manager
    
    host = settings.get('host', '127.0.0.1')
    port = settings.get('port', 8848)
    print(f"🤖 AIPython Agent Mode ({__version__})")
    print(f"🚀 Starting HTTP API server on {host}:{port}")
    
    # 初始化Agent管理器
    if not init_agent_manager(settings):
        print(f"❌ {T('Failed to initialize agent manager')}")
        return
    
    print(f"✅ {T('Agent manager initialized')}")
    print(f"🔗 API Documentation: http://{host}:{port}/docs")
    print(f"📊 Health Check: http://{host}:{port}/health")
    
    # 启动服务器
    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info" if settings.get('debug', False) else "warning"
        )
    except KeyboardInterrupt:
        print(f"\n⏹️  {T('Server stopped by user')}")
    except Exception as e:
        print(f"❌ {T('Server error')}: {e}")
        logger.error(f"Server error: {e}")