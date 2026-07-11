"""Sanity-check that PyTorch sees the GPU and can train on it."""
import torch

print(f"PyTorch:        {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"Device:         {torch.cuda.get_device_name(0)}")
    print(f"CUDA version:   {torch.version.cuda}")
    props = torch.cuda.get_device_properties(0)
    print(f"VRAM:           {props.total_memory / 1024**3:.1f} GB")
    print(f"Compute cap:    sm_{props.major}{props.minor}")

    # Tiny end-to-end training step on the GPU
    model = torch.nn.Linear(1024, 10).cuda()
    x = torch.randn(64, 1024, device="cuda")
    loss = model(x).sum()
    loss.backward()
    torch.cuda.synchronize()
    print("GPU forward/backward pass: OK")
else:
    raise SystemExit("ERROR: CUDA not available — check driver / torch build")
