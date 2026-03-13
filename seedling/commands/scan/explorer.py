import sys
from pathlib import Path
from seedling.core.filesystem import scan_dir_lines
from seedling.core.io import create_image_from_text
from .full import run_full

def run_explorer(args, target_path):
    out_dir_path = Path(args.outdir).resolve() if args.outdir else Path.cwd()
    out_dir_path.mkdir(parents=True, exist_ok=True)
    target_name = target_path.name or "root_dir"

    ext_map = {'md': '.md', 'txt': '.txt', 'image': '.png'}
    out_name = args.name or f"{target_name}{ext_map[args.format]}"
    
    if not any(out_name.endswith(ext) for ext in ext_map.values()):
        out_name += ext_map[args.format]
        
    final_file = out_dir_path / out_name
    
    stats = {"dirs": 0, "files": 0}
    lines = scan_dir_lines(target_path, max_depth=args.depth, show_hidden=args.show_hidden, excludes=args.exclude, stats=stats, text_only=args.text_only)
    
    sys.stdout.write(f"\r✅ Scan Complete! [ 📁 {stats['dirs']} dirs | 📄 {stats['files']} files ]            \n")
    sys.stdout.flush()
    
    root_name = target_path.name or str(target_path)
    tree_text = f"{root_name}/\n" + "\n".join(lines) + f"\n\n[ 📁 {stats['dirs']} directories, 📄 {stats['files']} files ]"
    
    full_content = ""
    if args.full:
        full_content = run_full(args, target_path)
        if args.format == 'image':
            args.format = 'md'
            final_file = final_file.with_suffix('.md')

    success = False
    if args.format == 'md':
        with open(final_file, 'w', encoding='utf-8') as f:
            f.write(f"# 📁 Directory Structure Stats: `{target_path}`\n\n```text\n{tree_text}\n```\n")
            f.write(full_content)
        success = True
    elif args.format == 'txt':
        with open(final_file, 'w', encoding='utf-8') as f:
            f.write(tree_text + "\n")
            f.write(full_content)
        success = True
    elif args.format == 'image':
        success = create_image_from_text(tree_text, final_file, len(lines))
            
    if success:
        print(f"🎉 SUCCESS! Directory structure saved to:\n   👉 {final_file}\n")