module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  extends: [
    'plugin:vue/vue3-recommended',
    'prettier',
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  overrides: [
    {
      files: ['src/views/**/*.vue'],
      rules: { 'vue/multi-word-component-names': 'off' },
    },
  ],
  rules: {
    'no-restricted-syntax': [
      'error',
      {
        selector: "CallExpression[callee.name='dayjs'][arguments.0.type='Identifier']",
        message: '请使用 utils/datetime 的 parseBackendTime 处理后端时间字符串',
      },
      {
        selector: "NewExpression[callee.name='Date'][arguments.0.type='Identifier']",
        message: '请使用 utils/datetime 的 parseBackendTime 处理后端时间字符串',
      },
    ],
    'no-restricted-imports': [
      'error',
      { patterns: ['@/*'] },
    ],
  },
}
