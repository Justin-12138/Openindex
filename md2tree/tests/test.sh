curl -X POST "https://open.bigmodel.cn/api/coding/paas/v4/chat/completions" \
-H "Content-Type: application/json" \
-H "Authorization: Bearer f7256e238a4e4f978918a26ac09ab5ad.dxTrbSoVLd3KYCPU" \
-d '{
    "model": "glm-4.7",
    "messages": [
        {
            "role": "system",
            "content": "你是一个有用的AI助手。"
        },
        {
            "role": "user",
            "content": "你好，请介绍一下自己。"
        }
    ],
    "temperature": 1.0,
    "stream": true
}'