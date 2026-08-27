from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

connected_clients = []


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await websocket.accept()

    connected_clients.append(websocket)

    print("WebSocket client connected")

    try:
        while True:
            # Keep connection alive and listen for messages
            data = await websocket.receive_text()

            print("Received:", data)

    except WebSocketDisconnect:
        print("WebSocket client disconnected")

        if websocket in connected_clients:
            connected_clients.remove(websocket)