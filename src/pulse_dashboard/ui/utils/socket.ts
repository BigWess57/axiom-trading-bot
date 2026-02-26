import { io } from "socket.io-client";

const SOCKET_URL = "http://localhost:8000";

export const socket = io(SOCKET_URL, {
  transports: ["websocket"],
  reconnectionAttempts: 5,
  autoConnect: true,
});
