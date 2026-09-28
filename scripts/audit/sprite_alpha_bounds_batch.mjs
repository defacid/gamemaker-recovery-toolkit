import sharp from "sharp";
let input = "";
for await (const chunk of process.stdin) input += chunk;
const groups = JSON.parse(input), output = {};
for (const [key, files] of Object.entries(groups)) {
  let left=Infinity,top=Infinity,right=-1,bottom=-1;
  for (const file of files) {
    const {data,info}=await sharp(file).ensureAlpha().raw().toBuffer({resolveWithObject:true});
    for(let y=0;y<info.height;y++) for(let x=0;x<info.width;x++) if(data[(y*info.width+x)*4+3]>0){left=Math.min(left,x);top=Math.min(top,y);right=Math.max(right,x);bottom=Math.max(bottom,y);}
  }
  if(right<0)({left,top,right,bottom}={left:0,top:0,right:0,bottom:0});
  output[key]={left,top,right,bottom};
}
process.stdout.write(JSON.stringify(output));
