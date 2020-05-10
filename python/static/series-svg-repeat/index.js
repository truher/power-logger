//d3.text('repeat-data.csv').then(text => {
d3.json('/summarydata').then(data => {
    //const data = d3.csvParseRows(text, d => d.map(s => Number(s)));
    //data = [
      //[1,2,3,4,5,6,7,8,9],
      //[4,5,6,7,8,9,8,7,6]
    //data = [
    //  [{x:1585789200000000000,y:1},{x:1585760400000000000,y:4},{x:1585746000000000000,y:1}],
    //  [{x:1585789200000000000,y:4},{x:1585760400000000000,y:8},{x:1585746000000000000,y:2}]
    //];
    xdata = [
      [[1585789200000000000,1],[1585760400000000000,4],[1585746000000000000,1]],
      [[1585789200000000000,4],[1585760400000000000,8],[1585746000000000000,2]]
    ];
// this is what i have:
    seriesdata = 
[
//total
[
[1585720800000000000,24.2261],
[1585706400000000000,18.9523],
[1585717200000000000,3.86194],
[1585782000000000000,9.08982]
],
//load1
[
[1585720800000000000,0.46035299999999996],
[1585778400000000000,1.0564200000000001]
],
//load2
[
[1585713600000000000,0.310488],
[1585728000000000000,0.200454],
[1585735200000000000,3.5253099999999997],
[1585746000000000000,0.000906783],
[1585789200000000000,1.91612]
],
//load3
[
[1585702800000000000,14.5199],
[1585742400000000000,0.08817269999999999],
[1585756800000000000,0.9179370000000001]
],
//load4
[
[1585753200000000000,0.07090210000000001],
[1585760400000000000,10.1483]
],
//load5
[
[1585774800000000000,5.05705]
],
//load6
[
[1585724400000000000,0.295213],
[1585731600000000000,5.6895],
[1585749600000000000,0.7299399999999999],
[1585764000000000000,0.137005],
[1585785600000000000,0.337744],
[1585792800000000000,0.598398]
],
//load7
[
[1585699200000000000,24.2261],
[1585767600000000000,1.47666],
[1585771200000000000,2.17367]
],
//load8
[
[1585710000000000000,11.6143],
[1585738800000000000,2.28713]
]
];


// THIS IS THE TARGET

rd = [
    ["total",[
        [1,"total",2],[2,"total",3]
    ]],
    ["load1", [
        [3,"load1",4],[5,"load1",6]
    ]],
    ["load2",[
        [3,"load2",4],[5,"load2",6]
    ]]
]
console.log(seriesdata);
    realdata = data;
    xrealdata = 
[
[1585699200000000000,"load7",24.2261],
[1585702800000000000,"load3",14.5199],
[1585706400000000000,"total",18.9523],
[1585710000000000000,"load8",11.6143],
[1585713600000000000,"load2",0.310488],
[1585717200000000000,"total",3.86194],
[1585720800000000000,"load1",0.46035299999999996],
[1585724400000000000,"load6",0.295213],
[1585728000000000000,"load2",0.200454],
[1585731600000000000,"load6",5.6895],
[1585735200000000000,"load2",3.5253099999999997],
[1585738800000000000,"load8",2.28713],
[1585742400000000000,"load3",0.08817269999999999],
[1585746000000000000,"load2",0.000906783],
[1585749600000000000,"load6",0.7299399999999999],
[1585753200000000000,"load4",0.07090210000000001],
[1585756800000000000,"load3",0.9179370000000001],
[1585760400000000000,"load4",10.1483],
[1585764000000000000,"load6",0.137005],
[1585767600000000000,"load7",1.47666],
[1585771200000000000,"load7",2.17367],
[1585774800000000000,"load5",5.05705],
[1585778400000000000,"load1",1.0564200000000001],
[1585782000000000000,"total",9.08982],
[1585785600000000000,"load6",0.337744],
[1585789200000000000,"load2",1.91612],
[1585792800000000000,"load6",0.598398]];

grped = d3.groups(realdata, d=>d[1])
grped.sort((a,b)=>d3.ascending(a[0],b[0]));
console.log("GROUPED");
console.log(grped);
console.log(JSON.stringify(grped));
labels = grped.map(x=>x[0]);
console.log(JSON.stringify(labels));
seriesdata = grped.map(x => x[1]);

//labels = ['total','load1','load2','load3','load4','load5','load6','load7','load8'];
//console.log(realdata);
// what i want is:
// [[1,2,3] // row for total
    console.log("================seriesdata");
    console.log(JSON.stringify(seriesdata));
    console.log(seriesdata.length);

    data = seriesdata;
    alldata = data.flat();
   // x_minmax = alldata.reduce((acc, cur) =>
   //     [Math.min(cur.x, acc[0]), Math.max(cur.x, acc[1])],
   //     [Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY]
   // );
   //// y_minmax = alldata.reduce((acc, cur) =>
   //     [Math.min(cur.y, acc[0]), Math.max(cur.y, acc[1])],
   //     [Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY]
   // );
   // xmin = new Date(x_minmax[0]/1e6);
   // xmax = new Date(x_minmax[1]/1e6);
   // ymin = y_minmax[0];
   // ymax = y_minmax[1];


    //const xScale = d3.scaleLinear().domain([0, data.length - 1]).range([0,400]);
    //const yScale = d3.scaleLinear().domain([0, 60]).range([200,0]);
    //const xScale = d3.scaleLinear();
    //const yScale = d3.scaleLinear();
    //const xScale = d3.scaleLinear().domain([0, 10]).range([0,400]);
    //const yScale = d3.scaleLinear().domain([0, 10]).range([200,0]);

    const line = fc
        .seriesSvgLine()
        //.crossValue((_, i) => i)
        //.mainValue(d => d.y)
        //.mainValue(d => d[1])
        .mainValue(d => d[2])
        //.crossValue(d => new Date(d.x/1e6));
        .crossValue(d => new Date(d[0]/1e6));

    //const color = d3.scaleOrdinal([0,1], d3.schemeCategory10);
    //const color = d3.scaleOrdinal([0,1,2,3,4,5,6,7,8],d3.schemeCategory10);
    const color = d3.scaleOrdinal(d3.range(data.length),d3.schemeCategory10);

    const series = fc
        .seriesSvgRepeat()
        .orient('horizontal')
        .series(line)
        .decorate(sel => { // outer level == color
            sel.attr('stroke', (_, i) => color(i));
        });

    //xExtent = fc.extentLinear().accessors([(_,i)=>i]);
    //xExtent = fc.extentLinear().accessors([(d,i)=>{
        //console.log("X EXTENT");
        //console.log(d);
        //console.log(i);
        //x = d.x;
        //console.log(x);
        //return x;
    //}]);
    //yExtent = fc.extentLinear().accessors([d=>{return d.y;}]);
    //yExtent = fc.extentLinear().accessors([d=>{return d[1];}]);
    yExtent = fc.extentLinear().accessors([d=>{return d[2];}]);
    //xExtent = fc.extentTime().accessors([d=>new Date(d.x/1e6)]);
    xExtent = fc.extentTime().accessors([d=>new Date(d[0]/1e6)]);

    //const xScale = d3.scaleTime().domain([xmin, xmax]);
    const xScale = d3.scaleTime();
    //const xScale = d3.scaleLinear().domain([0, 10000]);
    //const yScale = d3.scaleLinear().domain([ymin, ymax]);
    const yScale = d3.scaleLinear();
    //const xScale = d3.scaleLinear();
    //const yScale = d3.scaleLinear();
    console.log("FLAT");
    //console.log(data.flat());
    console.log(alldata);

    const chart = fc.chartCartesian(xScale, yScale)
        //.xDomain(xExtent(data.flat()))
        ////.yDomain(yExtent(data.flat()))
        .xDomain(xExtent(alldata))
        .yDomain(yExtent(alldata))
        .chartLabel('chart label')
        .xLabel('x label')
        .yLabel('y label')
        .yOrient('left')
        .svgPlotArea(series);

    d3.select('div#foo').datum(data).call(chart);

  var legend = d3.legendColor().shapeWidth(30)
    .orient('vertical').scale(color).labels(labels);

  d3.select('div#foo d3fc-group d3fc-svg svg').call(legend);

});
