-- Validação resumida da carga inicial.
SELECT 'usuarios' AS entidade, COUNT(*) AS quantidade FROM usuarios
UNION ALL SELECT 'campanhas', COUNT(*) FROM campanhas
UNION ALL SELECT 'personagens', COUNT(*) FROM personagens
UNION ALL SELECT 'tipos_pokemon', COUNT(*) FROM tipos_pokemon
UNION ALL SELECT 'especies_pokemon', COUNT(*) FROM especies_pokemon
UNION ALL SELECT 'formas_pokemon', COUNT(*) FROM formas_pokemon
UNION ALL SELECT 'golpes', COUNT(*) FROM golpes
UNION ALL SELECT 'naturezas', COUNT(*) FROM naturezas
UNION ALL SELECT 'status_condicoes', COUNT(*) FROM status_condicoes
UNION ALL SELECT 'pokemons', COUNT(*) FROM pokemons
ORDER BY entidade;

-- Registros sem relacionamentos obrigatórios.
SELECT f.codigo, f.nome
FROM formas_pokemon f
LEFT JOIN forma_pokemon_atributos a ON a.forma_pokemon_id = f.id
WHERE a.id IS NULL
ORDER BY f.nome;

SELECT p.id, p.apelido
FROM pokemons p
LEFT JOIN formas_pokemon f ON f.id = p.forma_pokemon_id
WHERE f.id IS NULL;
