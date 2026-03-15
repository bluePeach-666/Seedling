from seedling.core.filesystem import get_full_context
from seedling.core.logger import logger

def run_full(args, target_path):
    logger.info(f"\n🚀 Power Mode Enabled! Gathering file contents...")
    if args.format == 'image':
        logger.warning("Power Mode cannot be exported as an image. Defaulting to Markdown (.md).")

    context_list = get_full_context(
        target_path, 
        show_hidden=args.show_hidden, 
        excludes=args.exclude,
        text_only=getattr(args, 'text_only', False),
        max_depth=args.depth,
        quiet=args.quiet
    )
    
    sections = ["\n\n" + "="*60, "📁 FULL PROJECT CONTENT", "="*60 + "\n"]
    for rel_path, content in context_list:
        sections.append(f"### FILE: {rel_path}")
        lang = rel_path.suffix.lstrip('.')
        
        max_ticks = 2
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped.startswith('`'):
                ticks = len(stripped) - len(stripped.lstrip('`'))
                if ticks > max_ticks:
                    max_ticks = ticks
        
        fence = '`' * (max_ticks + 1)
        sections.append(f"{fence}{lang}\n{content}\n{fence}\n")
        
    logger.info(f"✅ Aggregated {len(context_list)} files.")
    return "\n".join(sections)