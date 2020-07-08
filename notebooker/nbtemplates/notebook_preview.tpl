{% extends 'full.tpl'%}
{% block any_cell %}
{% if 'parameters' in cell['metadata'].get('tags', []) %}
    <div style="border:solid yellow">
        {{ super() }}
    </div>
{% else %}
    {{ super() }}
{% endif %}
{% endblock any_cell %}
