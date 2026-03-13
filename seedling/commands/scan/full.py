from seedling.core.filesystem import get_full_context

def run_full(args, target_path):
    print(f"\n🚀 Power Mode Enabled! Gathering file contents...")
    if args.format == 'image':
        print("⚠️  WARNING: Power Mode cannot be exported as an image. Defaulting to Markdown (.md).")

    context_list = get_full_context(
        target_path, 
        show_hidden=args.show_hidden, 
        excludes=args.exclude,
        text_only=getattr(args, 'text_only', False),
        max_depth=args.depth
    )
    
    sections = ["\n\n" + "="*60, "📁 FULL PROJECT CONTENT", "="*60 + "\n"]
    for rel_path, content in context_list:
        sections.append(f"### FILE: {rel_path}")
        lang = rel_path.suffix.lstrip('.')
        sections.append(f"```{lang}\n{content}\n```\n")
        
    print(f"\n✅ Aggregated {len(context_list)} files.")
    return "\n".join(sections)