import torch
import os
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers import TrainingArguments
from peft import LoraConfig, get_peft_model
from datasets import load_dataset
from trl import SFTConfig, SFTTrainer




# Model configuration
max_seq_length = 2048
# model_name = "meta-llama/Llama-3.2-3B-Instruct"
model_path = r'D:\work\models\Meta-Llama-3.2-3B-Instruct'
# Load model and tokenizer
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.bfloat16 if torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8 else torch.float16,
    device_map="auto"
)

tokenizer = AutoTokenizer.from_pretrained(
    model_path,
    model_max_length=max_seq_length,
    padding_side="right"
)

# Configure LoRA
lora_config = LoraConfig(
    r=16,  # rank
    lora_alpha=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0,
    bias="none",
    task_type="CAUSAL_LM"
)

# Apply PEFT
model = get_peft_model(model, lora_config)

# Define prompt template for formatting
llama31_prompt = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{}<|eot_id|><|start_header_id|>user<|end_header_id|>

{}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{}<|eot_id|>"""

def formatting_prompts_func(examples):
    fields = examples["conversations"]
    texts = []
    for convos in fields:
        instruction = convos[0]['value']
        input_text = convos[1]['value']
        output = convos[2]['value']
        text = llama31_prompt.format(instruction, input_text, output)
        texts.append(text)
    return {"text": texts}

# Load and process dataset
dataset = load_dataset("json", data_files={"train": "data.jsonl"}, split="train")
dataset = dataset.map(formatting_prompts_func, batched=True)

# Configure training arguments
training_args = TrainingArguments(
    output_dir="outputs",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    warmup_steps=5,
    num_train_epochs=3,
    learning_rate=2e-4,
    fp16=(torch.cuda.is_available() and not (torch.cuda.get_device_capability()[0] >= 8)),
    bf16=(torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8),
    logging_steps=1,
    optim="adamw_torch",
    weight_decay=0.01,
    lr_scheduler_type="linear",
    seed=3407,
    report_to="none"
)

# Record starting memory usage
if torch.cuda.is_available():
    gpu_stats = torch.cuda.get_device_properties(0)
    start_gpu_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
    max_memory = round(gpu_stats.total_memory / 1024 / 1024 / 1024, 3)
    print(f"GPU = {gpu_stats.name}. Max memory = {max_memory} GB.")
    print(f"{start_gpu_memory} GB of memory reserved.")

# Initialize SFT trainer without custom preprocessing for now
sft_config = SFTConfig(
    max_seq_length=max_seq_length,
    packing=False,
    **training_args.to_dict()  # Pass training arguments to SFTConfig
)

# Create trainer using SFTConfig
trainer = SFTTrainer(
    model=model,
    args=sft_config,
    train_dataset=dataset,  # Use original dataset
    data_collator=None,    # Let the trainer handle this
)

# Train the model
trainer_stats = trainer.train()

# Report training statistics and memory usage
if torch.cuda.is_available():
    used_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
    used_memory_for_lora = round(used_memory - start_gpu_memory, 3)
    used_percentage = round(used_memory / max_memory * 100, 3)
    lora_percentage = round(used_memory_for_lora / max_memory * 100, 3)
    print(f"{trainer_stats.metrics['train_runtime']} seconds used for training.")
    print(f"{round(trainer_stats.metrics['train_runtime']/60, 2)} minutes used for training.")
    print(f"Peak reserved memory = {used_memory} GB.")
    print(f"Peak reserved memory for training = {used_memory_for_lora} GB.")
    print(f"Peak reserved memory % of max memory = {used_percentage} %.")
    print(f"Peak reserved memory for training % of max memory = {lora_percentage} %.")

# Save the model
output_dir = "model"
os.makedirs(output_dir, exist_ok=True)
model.save_pretrained(output_dir)
tokenizer.save_pretrained(output_dir)

# Example inference
def run_inference(prompt):
    # Set model to evaluation mode
    model.eval()
    
    # Format the messages
    messages = [{"role": "user", "content": prompt}]
    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt"
    ).to(model.device)
    
    # Generate response
    with torch.no_grad():
        outputs = model.generate(
            input_ids=inputs, 
            max_new_tokens=128, 
            do_sample=True,
            temperature=1.5, 
            top_p=0.9
        )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response

# Example usage (uncomment to test)
# test_prompt = "Describe a tall tower in the capital of France."
# response = run_inference(test_prompt)
# print(response)