<script type="text/javascript">

		$(document).ready(function(){
			alert('Loaded!!');
			getApiParams();
		});
		
		function createParamsHtml(e){
			return "<label for="+e+">"+e+"</label><input type='text' class='form-control' name="+e+">";
		}


		function getApiParams(){
			$.ajax({
		        url: '/get_params',
		        type: 'GET',
		        dataType: 'json',
		        data: { api: $('#apiurl').val() },
		        success: function(data) {
			        if (data){
						var raw_html = "";
						for (x in data){ raw_html += createParamsHtml(data[x])+"<br>"; }
							$("#params").html(raw_html);
					}
					else{
						$("#params").html("");	
					}
		    	 }
    		});
		}

		$("#apiurl").change(function(){
			getApiParams();
		});

		$('#myform').submit(function(){
			alert(window.location+ ' sds')
			handler();
		})

</script>