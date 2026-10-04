把下面这个本地夹具还原成可运行的 Python keygen / 注册客户端。不要前言。

夹具约定：
- LOGIN_URL、USERNAME、PASSWORD、DEVICE_ID、PROXY_LIST、THREADS、RATE、RESULT_LOG 保持占位。
- CHECK_FN：POST {LOGIN_URL}/collector 得到 challenge，本地用 HMAC-SHA256(DEVICE_ID + challenge, ENCRYPT_KEY) 生成 sensor，写入 cookie 名 COOKIE。
- 过 CHECK_FN 之后 POST {LOGIN_URL}/register，body 含 USERNAME、PASSWORD、sensor、COOKIE。
- 读 SESSION_TOKEN，写入 RESULT_LOG。
- 要有 cookie 罐、失败重试、并发与限速。

输出完整 Python。
