import subprocess
import json
import os

class JSXCliParser:
    def __init__(self):
        self._setup_parser()
        
    def _setup_parser(self):
        """Setup the JavaScript/JSX parser."""
        try:
            if not os.path.exists('tree-sitter-javascript'):
                print("Cloning tree-sitter-javascript repository...")
                result = subprocess.run(
                    ['git', 'clone', 'https://github.com/tree-sitter/tree-sitter-javascript.git'],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print(f"Error cloning repository: {result.stderr}")
                    return
                
                print("Installing dependencies...")
                result = subprocess.run(
                    ['npm', 'install'],
                    cwd='tree-sitter-javascript',
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print(f"Error installing dependencies: {result.stderr}")
                    return
                
                print("Generating parser...")
                result = subprocess.run(
                    ['tree-sitter', 'generate'],
                    cwd='tree-sitter-javascript',
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print(f"Error generating parser: {result.stderr}")
                    return
                
            print("Parser setup complete.")
        except Exception as e:
            print(f"Error during setup: {str(e)}")

    def parse_file(self, file_path):
        """Parse a JSX file using tree-sitter CLI."""
        try:
            print(f"Parsing file: {file_path}")
            if not os.path.exists(file_path):
                print(f"Error: File not found: {file_path}")
                return None
                
            # Run tree-sitter parse command
            result = subprocess.run(
                ['tree-sitter', 'parse', os.path.abspath(file_path)],
                cwd='tree-sitter-javascript',
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"Error parsing file: {result.stderr}")
                return None
                
            if not result.stdout:
                print("Warning: Parser produced no output")
                
            return result.stdout
            
        except Exception as e:
            print(f"Error running tree-sitter: {str(e)}")
            return None

    def parse_and_save(self, input_file, output_file):
        """Parse a JSX file and save the output to a file."""
        ast = self.parse_file(input_file)
        if ast:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(ast)
                print(f"AST saved to {output_file}")
                return True
            except Exception as e:
                print(f"Error saving output: {str(e)}")
                return False
        return False

# Example usage
if __name__ == "__main__":
    parser = JSXCliParser()
    if parser.parse_and_save('test.jsx', 'jsx_ast.txt'):
        print("Parsing complete.")
    else:
        print("Failed to parse the file.") 