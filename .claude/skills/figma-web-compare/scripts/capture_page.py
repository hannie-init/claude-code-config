#!/usr/bin/env python3
"""Connect to existing Chrome via CDP and extract visible text content."""

import sys
import json
import argparse
import urllib.request
import time


def get_pages(port):
    try:
        url = f"http://localhost:{port}/json"
        resp = urllib.request.urlopen(url, timeout=5)
        return json.loads(resp.read())
    except Exception:
        return None


def evaluate_js(ws_url, js_code, timeout=15):
    try:
        import websocket
    except ImportError:
        print(json.dumps({
            "error": "websocket-client 패키지가 없습니다.",
            "hint": "pip install websocket-client"
        }), flush=True)
        sys.exit(1)

    ws = websocket.WebSocket()
    try:
        ws.connect(ws_url, timeout=timeout, suppress_origin=True)
    except Exception as e:
        err = str(e)
        if "403" in err or "remote-allow-origins" in err:
            import re as _re
            port_match = _re.search(r":(\d+)/", ws_url)
            p = port_match.group(1) if port_match else "9222"
            return {
                "error": "WebSocket 연결 실패 (403 Forbidden): Chrome을 --remote-allow-origins=* 플래그로 재시작하세요.",
                "hint": f'open -a "Google Chrome" --args --remote-debugging-port={p} --remote-allow-origins=*',
            }
        return {"error": f"WebSocket 연결 실패: {e}"}

    cmd = json.dumps({
        "id": 1,
        "method": "Runtime.evaluate",
        "params": {"expression": js_code, "returnByValue": True}
    })
    try:
        ws.send(cmd)

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                ws.settimeout(max(0.5, deadline - time.time()))
                msg = json.loads(ws.recv())
                if msg.get("id") == 1:
                    return msg
            except Exception:
                break
    finally:
        try:
            ws.close()
        except Exception:
            pass

    return {"error": "응답 타임아웃"}


def main():
    parser = argparse.ArgumentParser(description="Chrome CDP 연결 후 텍스트 추출")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--output", default="/tmp/figma_compare_content.json")
    parser.add_argument("--page-url", default=None, help="URL 패턴으로 탭 선택")
    args = parser.parse_args()

    pages = get_pages(args.port)
    if pages is None:
        print(json.dumps({
            "error": f"Chrome에 연결할 수 없습니다 (port {args.port})",
            "hint": (
                f'open -a "Google Chrome" --args --remote-debugging-port={args.port}'
            )
        }), flush=True)
        sys.exit(1)

    page_tabs = [p for p in pages if p.get("type") == "page"]
    if not page_tabs:
        print(json.dumps({"error": "열린 탭이 없습니다. Chrome에서 비교할 페이지를 먼저 열어주세요."}), flush=True)
        sys.exit(1)

    target = page_tabs[-1]
    if args.page_url:
        matched = [t for t in page_tabs if args.page_url in t.get("url", "")]
        if matched:
            target = matched[-1]
        else:
            print(json.dumps({
                "error": f"URL에 '{args.page_url}'이 포함된 탭을 찾을 수 없습니다.",
                "available_pages": [{"index": i, "url": t.get("url"), "title": t.get("title")}
                                     for i, t in enumerate(page_tabs)]
            }), flush=True)
            sys.exit(1)

    ws_url = target.get("webSocketDebuggerUrl")
    if not ws_url:
        print(json.dumps({"error": "탭의 WebSocket URL을 찾을 수 없습니다."}), flush=True)
        sys.exit(1)

    response = evaluate_js(ws_url, "document.body.innerText")

    if "error" in response:
        print(json.dumps({"error": response["error"]}), flush=True)
        sys.exit(1)

    result_obj = response.get("result", {}).get("result", {})
    text_content = result_obj.get("value", "")

    pages_info = [{"index": i, "url": t.get("url"), "title": t.get("title")}
                  for i, t in enumerate(page_tabs)]

    result = {
        "url": target.get("url", ""),
        "title": target.get("title", ""),
        "text_content": text_content,
        "all_pages": pages_info,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "success": True,
        "output": args.output,
        "url": target.get("url", ""),
        "title": target.get("title", ""),
        "available_pages": len(page_tabs),
        "text_length": len(text_content),
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
