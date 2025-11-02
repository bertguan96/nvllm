vllm serve ~/Qwen3Guard-Gen-8B \
    --host 0.0.0.0 \
    --port 6006 \
    --tensor-parallel-size 1 \
    --max-model-len 2048 \
    --gpu-memory-utilization 0.92 \
    --dtype bfloat16 \
    --trust-remote-code