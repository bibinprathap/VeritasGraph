from importlib import resources


def prompt(name: str) -> str:
    return (resources.files("veritasgraph.structured") / "prompts" / f"{name}.md").read_text(encoding="utf-8")
