// Purpose: Test fixture/configuration helper for vite Env Transform.
// Jest runs CommonJS; expose Vite's public env shape through process.env in tests.
module.exports = ({ types: t }) => ({
  visitor: {
    MemberExpression(path) {
      const { object, property } = path.node;
      if (object.type === 'MetaProperty' && object.meta.name === 'import' && object.property.name === 'meta' && property.name === 'env') {
        path.replaceWith(t.memberExpression(t.identifier('process'), t.identifier('env')));
      }
    },
  },
});
