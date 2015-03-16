$(function() {
  $( "#initialdate" ).datepicker({showOn: "button",
    buttonImage: "images/calendar.png",
    buttonImageOnly: true,
    dateFormat: 'yy-mm-dd',
    dayNamesMin: [ "Do", "Lu", "Ma", "Mi", "Ju", "Vi", "Sa" ],
    monthNames: [ "Enero", "Febrero", "Marzo", "Abril", 
                  "Mayo", "Junio", "Julio", "Agosto", 
                  "Septiembre", "Octubre", "Noviembre", 
                  "Diciembre"],
    minDate: new Date(2014, 7-1, 8),
    maxDate: "0" });
  $( "#finaldate" ).datepicker({showOn: "button", 
        buttonImage: "images/calendar.png", 
        buttonImageOnly: true,
        dateFormat: 'yy-mm-dd',
        dayNamesMin: [ "Do", "Lu", "Ma", "Mi", "Ju", "Vi", "Sa" ],
        monthNames: [ "Enero", "Febrero", "Marzo", "Abril", 
                      "Mayo", "Junio", "Julio", "Agosto", 
                      "Septiembre", "Octubre", "Noviembre", 
                      "Diciembre"],
        minDate: new Date(2014, 7-1, 8), 
        maxDate: "0" });
  $( "#nombre" )
        .selectmenu()
        .selectmenu( "menuWidget" )
        .addClass( "overflow" );
  $( "#variable" ).selectmenu();
  $( "input[type=submit]" ).button(); 
  var tab = $('#jinjadata').data();
  var va = $('#va').data();
  console.log(va)
  $( "#visualizations" ).tabs({ active: tab,
        beforeActivate: function (event, ui) {
          switch (ui.newPanel.attr('id')) {
            case "visualizations-1":
                if (tab==1){
                      break;
                    } else{                
                  google.load('visualization', '1', {packages: ['annotatedtimeline'], callback: drawChartVA});
                  break;
                }
            case "visualizations-2":
                if (tab==1){
                  break;
                } else{                  
                  google.load('visualization', '1', {packages: ['annotatedtimeline'], callback: drawChartVB});
                  break;
                }
            case "visualizations-3":
                if (tab==2){
                  break;
                } else{                  
                  google.load('visualization', '1', {packages: ['annotatedtimeline'], callback: drawChartVC});
                  break;
                }
            case "visualizations-4":
                if (tab==3){
                  break;
                } else{                  
                  google.load('visualization', '1', {packages: ['annotatedtimeline'], callback: drawChartIA});
                  break;
                }
            case "visualizations-5":
                if (tab==4){
                  break;
                } else{                  
                  google.load('visualization', '1', {packages: ['annotatedtimeline'], callback: drawChartIB});
                  break;
                }
            case "visualizations-6":
                if (tab==5){
                  break;
                } else{                  
                  google.load('visualization', '1', {packages: ['annotatedtimeline'], callback: drawChartIC});
                  break;
                };
            case  "visualizations-7":
                if (tab==6){
                  break;
                } else{                  
                  google.load('visualization', '1', {packages: ['annotatedtimeline'], callback: drawChartP});
                  break;
                }
            case  "visualizations-8":
                if (tab==7){
                  break;
                } else{                  
                  google.load('visualization', '1', {packages: ['annotatedtimeline'], callback: drawChartFP});
                  break;
                }
            case  "visualizations-9":
                if (tab==8){
                  break;
                } else{                  
                  google.load('visualization', '1', {packages: ['annotatedtimeline'], callback: drawChartIneutro});
                  break;
                }
          }        
        }
      });
});