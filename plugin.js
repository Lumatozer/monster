module.exports = function(babel) {
  const { types: t } = babel;

  function generateUUID() {
    return '__' + Math.random().toString(36).substr(2, 9) + '__';
  }

  return {
    name: "transform-signal-to-hooks",
    visitor: {
      Program: {
        enter(path, state) {
          state.hasSignalImport = false;
          state.needsReactImports = new Set();
        },
        exit(path, state) {
          if (state.needsReactImports.size > 0) {
            addReactImports(path, state.needsReactImports);
          }
        }
      },

      ImportDeclaration(path, state) {
        const specifiers = path.node.specifiers;
        
        for (const spec of specifiers) {
          if ((t.isImportSpecifier(spec) && spec.imported.name === 'Signal') ||
              (t.isImportDefaultSpecifier(spec) && spec.local.name === 'Signal')) {
            if (path.node.source.value === '@aludayalu/signals') {
              state.hasSignalImport = true;
            }
          }
        }
      },

      FunctionDeclaration(path, state) {
        if (state.hasSignalImport) {
          transformFunction(path, state);
        }
      },

      ArrowFunctionExpression(path, state) {
        if (state.hasSignalImport) {
          transformFunction(path, state);
        }
      },

      FunctionExpression(path, state) {
        if (state.hasSignalImport) {
          transformFunction(path, state);
        }
      }
    }
  };

  function transformFunction(path, state) {
    const body = path.get('body');
    let transformations = [];

    body.traverse({
      VariableDeclaration(varPath) {
        const declarations = varPath.node.declarations;
        
        for (let i = 0; i < declarations.length; i++) {
          const decl = declarations[i];
          
          if (t.isArrayPattern(decl.id) && 
              t.isCallExpression(decl.init) && 
              t.isIdentifier(decl.init.callee, { name: 'Signal' })) {
            
            // Enforce signalID must be a string literal
            const signalID = decl.init.arguments[0];
            if (!t.isStringLiteral(signalID)) {
              throw new Error(
                `Signal ID must be a string literal. Found: ${signalID?.type || 'undefined'} at line ${decl.loc?.start?.line || 'unknown'}`
              );
            }
            
            // Validate signalID is not empty
            if (signalID.value.trim() === '') {
              throw new Error(
                `Signal ID cannot be empty string at line ${decl.loc?.start?.line || 'unknown'}`
              );
            }
            
            state.needsReactImports.add('useState');
            
            const arrayPattern = decl.id;
            const setSignalName = arrayPattern.elements[1].name;
            
            const defaultValue = decl.init.arguments[1];
            
            const randomUUID = generateUUID();
            
            arrayPattern.elements[1] = t.identifier(randomUUID);
            
            decl.init = t.callExpression(
              t.identifier('useState'),
              defaultValue ? [defaultValue] : []
            );
            
            transformations.push({
              varPath,
              setSignalName,
              signalID,
              randomUUID,
              defaultValue
            });
          }
        }
      }
    });

    transformations.forEach(({ varPath, setSignalName, signalID, randomUUID, defaultValue }) => {
      const setSignalDeclaration = t.variableDeclaration('var', [
        t.variableDeclarator(
          t.identifier(setSignalName),
          t.arrowFunctionExpression(
            [t.identifier('value')],
            t.callExpression(
              t.memberExpression(t.identifier('Signal'), t.identifier('setValue')),
              [signalID, t.identifier('value')]
            )
          )
        )
      ]);
      
      const onChangeCall = t.expressionStatement(
        t.callExpression(
          t.memberExpression(t.identifier('Signal'), t.identifier('onChange')),
          [signalID, t.identifier(randomUUID), t.stringLiteral(randomUUID), defaultValue || t.nullLiteral()]
        )
      );
      
      const parentBlock = varPath.getFunctionParent().get('body');
      const varIndex = parentBlock.node.body.indexOf(varPath.node);
      
      parentBlock.node.body.splice(varIndex + 1, 0, setSignalDeclaration, onChangeCall);
    });
  }

  function addReactImports(programPath, imports) {
    const importDeclaration = t.importDeclaration(
      Array.from(imports).map(name => 
        t.importSpecifier(t.identifier(name), t.identifier(name))
      ),
      t.stringLiteral('react')
    );

    const existingReactImport = programPath.node.body.find(node => 
      t.isImportDeclaration(node) && node.source.value === 'react'
    );

    if (existingReactImport) {
      const existingSpecifiers = existingReactImport.specifiers;
      const newSpecifiers = importDeclaration.specifiers.filter(newSpec => 
        !existingSpecifiers.some(existing => 
          t.isImportSpecifier(existing) && 
          t.isImportSpecifier(newSpec) && 
          existing.imported.name === newSpec.imported.name
        )
      );
      existingReactImport.specifiers.push(...newSpecifiers);
    } else {
      programPath.unshiftContainer('body', importDeclaration);
    }
  }
};