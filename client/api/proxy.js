import { createProxyMiddleware } from 'http-proxy-middleware';

export const config = {
  api: {
    bodyParser: false, // Disable body parsing for WebSocket proxying
  },
};

const proxy = createProxyMiddleware({
  target: 'https://192.168.0.151:8181',
  changeOrigin: true,
  secure: false,
  ws: true, // Enable WebSocket support
  onProxyReq: (proxyReq, req, res) => {
    console.log(
      '[PROXY] Forwarding request to:',
      `${proxyReq.protocol}//${proxyReq.host}${proxyReq.path}`
    );
  },
});

export default function handler(req, res) {
    console.log("test")
  return proxy(req, res, (result) => {
    if (result instanceof Error) {
      throw result;
    }
    throw new Error(`Request '${req.url}' is not proxied!`);
  });
}
