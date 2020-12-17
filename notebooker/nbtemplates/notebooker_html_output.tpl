{% extends 'full.tpl'%}
{% block html_head %}
{{ super() }}
<style type="text/css">

.btn {
  display: inline-block;
  text-align: center;
  text-decoration: none;
  margin: 2px 0;
  border: solid 1px transparent;
  border-radius: 4px;
  padding: 0.5em 1em;
  color: #ffffff;
  background-color: #9555af;
}

</style>

<!--[if mso]>
<style type="text/css">
div div.cell {
  border-style: none;
  margin-top: 4;
}
</style>
<![endif]-->

<script>
(function() {
  function addToggleCodeButton() {

    var hidden = true;
    var code_blocks = [
    	'.input',
    	'.prompt',
    	'.output_stream'
    ];
    var show_code = function(){
        code_blocks.forEach(
            function(block){
                $(block).show()
            }
        )
    };
	var hide_code = function(){
	    code_blocks.forEach(
	        function(block){
	            $(block).hide()
            }
        )
    };


	var bodyElement = $('#notebook-container')[0];
    var toggleDiv = document.createElement('div');
    var toggleButton = document.createElement('button');
    toggleButton.className = 'btn';
    toggleButton.onclick = function(){
    	if(hidden){ show_code() } else { hide_code() };
    	hidden = !hidden;
	};

    var toggleText = document.createTextNode('Toggle Code');
    toggleButton.appendChild(toggleText);
    toggleDiv.appendChild(toggleButton);
    bodyElement.insertBefore( toggleDiv, bodyElement.firstChild);

    // Default to hidden code
	hide_code()
  }

  document.addEventListener('DOMContentLoaded', addToggleCodeButton);
}());
</script>
{%- endblock html_head -%}

{% block stream %}
  {%- if resources.global_content_filter.include_output_prompt -%}
    {{ super() }}
  {%- endif -%}
{%- endblock stream %}
