import os

os.environ["XLA_FLAGS"] = '--xla_force_host_platform_device_count=8'

import copy
import jax

try:
    from lib.python.EasyDel import LlamaConfig, FlaxLlamaForCausalLM
    from lib.python.EasyDel.transform import llama_convert_hf_to_flax
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    cp = Path.cwd().__str__()
    sys.path.append(cp)
    from lib.python.EasyDel import LlamaConfig, FlaxLlamaForCausalLM
    from lib.python.EasyDel.transform import llama_convert_hf_to_flax
from jax import numpy as jnp
from transformers import LlamaForCausalLM
import torch
import numpy as np


def main():
    torch.manual_seed(42)

    config = LlamaConfig(
        hidden_size=128,
        num_attention_heads=8,
        num_key_value_heads=4,
        num_hidden_layers=2,
        intermediate_size=128,
        gradient_checkpointing=''
    )
    print('Model Config :\n', config)

    torch_model = LlamaForCausalLM(
        config=copy.deepcopy(config)
    )
    print(jax.devices('cpu'))
    params = {"params": llama_convert_hf_to_flax(torch_model.state_dict(), config, device=jax.devices('cpu')[0])}

    np_random_input_ids = np.random.randint(0, config.vocab_size, (1, 128))
    input_ids = torch.from_numpy(np_random_input_ids).reshape(1, -1).to(torch.long)
    flax_input_ids = jnp.asarray(np_random_input_ids, dtype=jnp.int32).reshape(1, -1)
    torch_output = torch_model(
        input_ids=input_ids
    )
    config.add_jax_args()
    print(config)
    try:

        flax_model = FlaxLlamaForCausalLM(
            config=config,
            dtype=jnp.float32,
            param_dtype=jnp.float32,
            _do_init=False, input_shape=(1, 6)
        )
        flax_output = flax_model(
            input_ids=flax_input_ids,
            params=params,

        )
        res = jnp.allclose(torch_output.logits.cpu().detach().numpy(), flax_output.logits, atol=1e-5)
        print('Mistral Huggingface Predictions :\n', torch_output.logits.cpu().detach().numpy(),
              '\nEasyDel Predictions: \n', flax_output.logits)
        if res:  # A Little Bit of humor
            print('\033[1;36mTest Passed Unfortunately 🥳')
        else:
            print('\033[1;31mTest Failed Successfully  🤕')

    except TypeError as e:
        print(e.__str__())


if __name__ == '__main__':
    main()
