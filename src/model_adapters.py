
from __future__ import annotations
from pathlib import Path
import json

class ModelUnavailable(RuntimeError):
    pass

class BaseAdapter:
    model_id="abstract"
    def generate(self,messages,**kwargs):
        raise NotImplementedError

class TransformersLocalAdapter(BaseAdapter):
    """Optional local Hugging Face Transformers adapter.

    This package intentionally does not auto-download a model. Point model_path
    to a local directory after the user has downloaded an approved model.
    """
    def __init__(self,model_path,device="cpu"):
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
        except Exception as e:
            raise ModelUnavailable("transformers is not installed") from e
        self.tok=AutoTokenizer.from_pretrained(model_path,local_files_only=True)
        self.model=AutoModelForCausalLM.from_pretrained(model_path,local_files_only=True)
        self.model.to(device)
        self.device=device
        self.model_id=str(model_path)

    def generate(self,messages,max_new_tokens=700,temperature=0.0):
        import torch
        inputs=self.tok.apply_chat_template(messages,add_generation_prompt=True,tokenize=True,
                                            return_tensors="pt").to(self.device)
        do_sample=temperature>0
        with torch.inference_mode():
            out=self.model.generate(inputs,max_new_tokens=max_new_tokens,do_sample=do_sample,
                                    temperature=temperature if do_sample else None)
        text=self.tok.decode(out[0][inputs.shape[-1]:],skip_special_tokens=True)
        return text

class OpenAICompatibleLocalAdapter(BaseAdapter):
    """Adapter for a LOCAL OpenAI-compatible server (e.g. llama.cpp/MLC/vLLM on localhost).

    No cloud endpoint is configured by default.
    """
    def __init__(self,base_url="http://127.0.0.1:8000/v1",model="local-model"):
        self.base_url=base_url.rstrip("/")
        self.model_id=model

    def generate(self,messages,max_new_tokens=700,temperature=0.0):
        import urllib.request
        payload=json.dumps({
            "model":self.model_id,"messages":messages,"temperature":temperature,
            "max_tokens":max_new_tokens
        }).encode()
        req=urllib.request.Request(self.base_url+"/chat/completions",data=payload,
                                   headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=300) as r:
            obj=json.loads(r.read().decode())
        return obj["choices"][0]["message"]["content"]
