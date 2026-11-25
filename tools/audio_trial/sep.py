import sys, torch, soundfile as sf
from demucs.pretrained import get_model
from demucs.apply import apply_model
D = sys.argv[1]
wav, sr = sf.read(D + "/src44.wav", dtype="float32"); x = torch.tensor(wav.T)[None]
m = get_model("htdemucs"); m.eval()
ref = x.mean(1, keepdim=True); mu, sd = ref.mean(), ref.std()
with torch.no_grad(): out = apply_model(m, (x - mu) / sd, device="cpu", split=True, overlap=0.25, progress=False)[0]
out = out * sd + mu
for name in m.sources: sf.write(D + "/" + name + ".wav", out[m.sources.index(name)].mean(0).numpy(), sr)
print("ok", m.sources)
