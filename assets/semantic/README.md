# 完整交付的多语言语义模型

`multilingual-e5-small.zip` 包含本机实际使用的三个模型文件，约 85 MB；普通 Git clone 和完整交付 ZIP 均携带它，无需 Git LFS 或另行访问模型网站。首次启动自动解压到本机 `.models/multilingual-e5-small`，逐文件校验长度与 SHA-256，最后才写就绪标记。模型推理依赖已纳入 `requirements.txt`，使用 CPU。

来源为 [Xenova/multilingual-e5-small](https://huggingface.co/Xenova/multilingual-e5-small/tree/761b726dd34fb83930e26aab4e9ac3899aa1fa78)，固定版本 `761b726dd34fb83930e26aab4e9ac3899aa1fa78`，基础模型为 [intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small)。文件指纹、池化和前缀以 `config/semantic_model.json` 为准；无权重修改或重新训练。

基础模型由 Microsoft 提供，采用 MIT 许可。保留 [MIT 许可原文](LICENSE.e5.txt)，来源 [Microsoft UniLM LICENSE](https://github.com/microsoft/unilm/blob/31c5b904ca1bf2afb4c234a6675c683a4e5fc7cd/LICENSE)。ONNX 转换由 Xenova 提供，模型卡标明上述基础模型。

手动修复：`python tools/setup_semantic_model.py`，只恢复本机展开目录，不修改发布配置。显式 `SKILLNET_ENCODER=lexical` 或自定义模型目录仍按部署配置处理；完整默认安装的 `/api/health` 应显示 `encoder.kind=dense-onnx`。
