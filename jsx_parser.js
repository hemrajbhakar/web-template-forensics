const Parser = require('tree-sitter');
const JavaScript = require('tree-sitter-javascript');
const fs = require('fs');

function nodeToJSON(node) {
    const result = {
        type: node.type,
        startPosition: node.startPosition,
        endPosition: node.endPosition,
        text: node.text
    };

    if (node.children.length > 0) {
        result.children = node.children.map(nodeToJSON);
    }

    return result;
}

async function parseJSX(filePath) {
    const parser = new Parser();
    parser.setLanguage(JavaScript);

    const sourceCode = fs.readFileSync(filePath, 'utf8');
    const tree = parser.parse(sourceCode);
    
    return nodeToJSON(tree.rootNode);
}

// Parse the test file
const inputFile = process.argv[2] || 'test.jsx';
const outputFile = process.argv[3] || 'jsx_ast.json';

parseJSX(inputFile)
    .then(ast => {
        fs.writeFileSync(outputFile, JSON.stringify(ast, null, 2));
        console.log(`Parsing complete. AST saved to ${outputFile}`);
    })
    .catch(err => {
        console.error('Error:', err);
    }); 