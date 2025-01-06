const fs = require('fs');
const path = require('path');
const firstFollow = require('first-follow')

function split(s, delimiter) {
    const idx = s.indexOf(delimiter);
    return [s.substring(0, idx), s.substring(idx)]
}

const filePath = path.join(__dirname, 'grammar.txt')
const data = fs.readFileSync(filePath, 'utf8');
const lines = data.split(/\r?\n/);
const rules = lines.reduce((rules, line) => {
    const [lhs, rhs] = split(line, ' ')
    const current_rule = rhs.split('|')
        .map((v) => v.trim())
        .filter((v) => v.length > 0)
        .map((v) => (v.toUpperCase() === 'EPSILON' ? null : v))
        .map((v) => (v != null && v.indexOf(' ') !== -1? new Array(...v.split(' ')) :[v]))
    return [...rules, ...current_rule.map((v) => ({
        left: lhs,
        right: new Array(...(v.filter((u) => u == null || !u.startsWith("#")))),
				right_with_actions: v
    }))]
}, [])


const { firstSets, followSets, predictSets } = firstFollow(rules);

const table = Object.entries(predictSets).reduce((acc, [k, v]) => {
    const rule = rules[Number(k) - 1];
    let res = acc;
    for (const char of v) {
        const tmp = (Object.hasOwn(res, rule.left) ? res[rule.left] : {});
        res = {
            ...res,
            [rule.left]: {
                ...tmp,
                [char]: rule.right_with_actions
            }
        }
    }
    return res
}, {});

const res = JSON.stringify( {
    firsts: firstSets,
    follows: followSets,
    predict: predictSets,
    rules: rules,
    table: table,
    non_terminals: Object.keys(followSets)
}, null, 2).replaceAll('\\u0000', '$').replaceAll("\u0000", '$')

fs.writeFileSync('grammar-output.json', res);
