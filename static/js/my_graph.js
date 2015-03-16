/*Funciones para las graficas Annotated Timeline de Google Chart Tools*/

function drawChartVA() {
  var va = $('#va').data();
  var voltaje_A = new google.visualization.AnnotatedTimeLine(document.getElementById('visualizations-1'));
  var data = new google.visualization.DataTable( {{ va|tojson|safe }}, 0.6);           
  voltaje_A.draw(data, {scaleType: 'maximized', 'thickness': 2, allValuesSuffix: ' Voltios'});
}            
google.load('visualization', '1', {packages: ['annotatedtimeline'], callback: drawChartVA});
      
function drawChartVB() {
  var vb = $('#vb').data();
  var annotatedtimeline = new google.visualization.AnnotatedTimeLine(document.getElementById('visualizations-2'));
  var data = new google.visualization.DataTable(vb, 0.6);           
  annotatedtimeline.draw(data, {scaleType: 'maximized', 'thickness': 2, allValuesSuffix: ' Voltios'});
}
google.load('visualization', '1', {packages: ['annotatedtimeline'], callback: drawChartVB});

function drawChartVC() {
  var vc = $('#vc').data();
  var annotatedtimeline = new google.visualization.AnnotatedTimeLine(document.getElementById('visualizations-3'));
  var data = new google.visualization.DataTable(vc, 0.6);           
  annotatedtimeline.draw(data, {scaleType: 'maximized', 'thickness': 2, allValuesSuffix: ' Voltios'});
}
google.load('visualization', '1', {packages: ['annotatedtimeline'], callback: drawChartVC});

function drawChartIA() {
  var ia = $('#ia').data();
  var annotatedtimeline = new google.visualization.AnnotatedTimeLine(document.getElementById('visualizations-4'));
  var data = new google.visualization.DataTable(ia, 0.6);           
  annotatedtimeline.draw(data, {scaleType: 'maximized', 'thickness': 2, allValuesSuffix: ' Amperios'});
}
google.load('visualization', '1', {packages: ['annotatedtimeline'], callback: drawChartIA});

function drawChartIB() {
  var ib = $('#ib').data();
  var annotatedtimeline = new google.visualization.AnnotatedTimeLine(document.getElementById('visualizations-5'));
  var data = new google.visualization.DataTable(ib, 0.6);           
  annotatedtimeline.draw(data, {scaleType: 'maximized', 'thickness': 2, allValuesSuffix: ' Amperios'});
}
google.load('visualization', '1', {packages: ['annotatedtimeline'], callback: drawChartIB});

function drawChartIC() {
  var ic = $('#ic').data();
  var annotatedtimeline = new google.visualization.AnnotatedTimeLine(document.getElementById('visualizations-6'));
  var data = new google.visualization.DataTable(ic, 0.6);           
  annotatedtimeline.draw(data, {scaleType: 'maximized', 'thickness': 2, allValuesSuffix: ' Amperios'});
}
google.load('visualization', '1', {packages: ['annotatedtimeline'], callback: drawChartIC});

function drawChartP() {
  var potencia = $('#potencia').data();
  var annotatedtimeline = new google.visualization.AnnotatedTimeLine(document.getElementById('visualizations-7'));
  var data = new google.visualization.DataTable(potencia, 0.6);           
  annotatedtimeline.draw(data, {scaleType: 'maximized', 'thickness': 2, allValuesSuffix: ' Watts'});
}
google.load('visualization', '1', {packages: ['annotatedtimeline'], callback: drawChartP});

function drawChartFP() {
  var FP = $('#FP').data();
  var annotatedtimeline = new google.visualization.AnnotatedTimeLine(document.getElementById('visualizations-8'));
  var data = new google.visualization.DataTable(FP, 0.6);           
  annotatedtimeline.draw(data, {scaleType: 'maximized', 'thickness': 2, displayExactValues: false});
}
google.load('visualization', '1', {packages: ['annotatedtimeline'], callback: drawChartFP});

function drawChartIneutro() {
  var Ineutro = $('#Ineutro').data();
  var annotatedtimeline = new google.visualization.AnnotatedTimeLine(document.getElementById('visualizations-9'));
  var data = new google.visualization.DataTable(Ineutro, 0.6);           
  annotatedtimeline.draw(data, {scaleType: 'maximized', 'thickness': 2, allValuesSuffix: ' Amperios'});
}
google.load('visualization', '1', {packages: ['annotatedtimeline'], callback: drawChartIneutro});