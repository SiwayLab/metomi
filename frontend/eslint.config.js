import js from "@eslint/js";
import pluginVue from "eslint-plugin-vue";
import globals from "globals";

export default [
    js.configs.recommended,
    ...pluginVue.configs["flat/essential"],
    {
        files: ["**/*.{js,vue}"],
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: "module",
            globals: {
                ...globals.browser,
                ...globals.node
            }
        },
        rules: {
            "vue/multi-word-component-names": "off",
            "no-unused-vars": "warn"
        }
    },
    {
        ignores: ["dist/**", "node_modules/**", "eslint.config.js", "vite.config.js"]
    }
];
