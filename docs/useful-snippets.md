# Useful snippets

## Database queries

### Number of labels in each state
```
SELECT latest_states.new_state, COUNT(*) AS num_labels_in_state
FROM (
	SELECT history.label_name, history.new_state
	FROM history
	JOIN (
		SELECT label_name, MAX(id) AS max_id
		FROM history
		GROUP BY label_name
	) states
	ON
		history.id = states.max_id AND
		history.label_name = states.label_name
) latest_states
GROUP BY latest_states.new_state;
```

### Latest state for all labels
```
SELECT history.label_name, history.created, history.new_state
FROM history
JOIN (
	SELECT label_name, MAX(id) AS max_id
	FROM history
	GROUP BY label_name
) latest_states
ON
	history.id = latest_states.max_id AND
	history.label_name = latest_states.label_name;
```

### Number of labels in a specific state

```
SELECT COUNT(*)
FROM history
JOIN (
	SELECT label_name, MAX(id) AS max_id
	FROM history
	GROUP BY label_name
) latest_states
ON
	history.id = latest_states.max_id AND
	history.label_name = latest_states.label_name
WHERE history.new_state = 'STATE_NAME';
```
