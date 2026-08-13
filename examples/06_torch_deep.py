"""Purpose: the torch integration as one instantiation of the general
system: rules route between models, and a MeTTa program trains as an
nn.Module under an ordinary optimizer, the autograd graph intact.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done, skip

try:
    import torch
except ImportError:
    skip("torch is not installed")

import pettorch
from petta import MeTTa

m = MeTTa().fresh_space()
pettorch.install(m)

# Symbolic routing over neural experts: which model runs is a rule.
double = torch.nn.Linear(1, 1, bias=False)
triple = torch.nn.Linear(1, 1, bias=False)
with torch.no_grad():
    double.weight.fill_(2.0)
    triple.weight.fill_(3.0)
pettorch.wrap(m, "expert-double", double)
pettorch.wrap(m, "expert-triple", triple)
m.run(
    "(route small expert-double)\n(route large expert-triple)\n"
    "(= (size-of $x) (if (< (t-item $x) 10.0) small large))\n"
    "(= (moe $x) (let $s (size-of $x)\n"
    "  (let $e (match (context-space) (route $s $r) $r) ($e $x))))"
)
check("routed small", m.run("!(t-item (moe (tensor (3.0))))"), [[6.0]])
check("routed large", m.run("!(t-item (moe (tensor (30.0))))"), [[90.0]])

# A MeTTa program as an nn.Module: equations fit by torch.optim.
m.run("(= (predict $x) (t-sum (t* (param w) $x)))")
model = pettorch.MettaModule(m, "predict", params={"w": torch.zeros(2)})
optimizer = torch.optim.SGD(model.parameters(), lr=0.05)
x, target = torch.tensor([1.0, 2.0]), torch.tensor(8.0)
for _ in range(200):
    optimizer.zero_grad()
    loss = torch.nn.functional.mse_loss(model(x), target)
    loss.backward()
    optimizer.step()
check("equations trained to the target", round(float(model(x)), 2), 8.0)
done("06_torch_deep")
