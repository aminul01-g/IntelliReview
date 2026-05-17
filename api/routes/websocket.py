import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status, Depends
from api.auth import get_current_user
from api.database import get_db
from sqlalchemy.orm import Session
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()

class AnalysisProgressManager:
    """
    Manages active WebSocket connections for analysis progress updates.
    """
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, analysis_id: str, websocket: WebSocket):
        await websocket.accept()
        if analysis_id not in self.active_connections:
            self.active_connections[analysis_id] = []
        self.active_connections[analysis_id].append(websocket)
        logger.info(f"WebSocket connected for analysis {analysis_id}")

    def disconnect(self, analysis_id: str, websocket: WebSocket):
        if analysis_id in self.active_connections:
            self.active_connections[analysis_id].remove(websocket)
            if not self.active_connections[analysis_id]:
                del self.active_connections[analysis_id]
        logger.info(f"WebSocket disconnected for analysis {analysis_id}")

    async def broadcast_status(self, analysis_id: str, status_update: Dict):
        """
        Push a status update to all clients watching this analysis.
        """
        if analysis_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[analysis_id]:
                try:
                    await connection.send_json(status_update)
                except Exception:
                    disconnected.append(connection)

            for conn in disconnected:
                self.disconnect(analysis_id, conn)

progress_manager = AnalysisProgressManager()

@router.websocket("/ws/analysis/{analysis_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    analysis_id: str,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time analysis progress.
    Expected flow: client connects -> server pushes status updates -> analysis completes.
    """
    # Auth check for WebSocket: Client must send token in query param or initial message
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.HTTP_401_UNAUTHORIZED)
        return

    try:
        # Validate token using existing auth logic
        from api.auth import jwt
        from config.settings import settings
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise Exception("Invalid token")
    except Exception:
        await websocket.close(code=status.HTTP_401_UNAUTHORIZED)
        return

    await progress_manager.connect(analysis_id, websocket)

    try:
        # Keep connection open, we only push data from the worker/Celery side
        while True:
            await websocket.receive_text() # Keep-alive / Heartbeat
    except WebSocketDisconnect:
        progress_manager.disconnect(analysis_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for analysis {analysis_id}: {e}")
        progress_manager.disconnect(analysis_id, websocket)

# This function will be called by Celery tasks to push updates
async def push_analysis_update(analysis_id: str, stage: str, percentage: int, message: str):
    """
    Utility to be called from within the analysis pipeline.
    """
    await progress_manager.broadcast_status(analysis_id, {
        "stage": stage,
        "percentage": percentage,
        "message": message
    })
