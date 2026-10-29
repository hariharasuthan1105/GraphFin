import { jsPDF } from 'jspdf';

const C = {ink:'#22262D', muted:'#59616E', red:'#A52C3B', pale:'#F3F5F7', line:'#DDE1E6', white:'#FFFFFF'};
export class AuditLayout {
  readonly doc = new jsPDF({unit:'mm',format:'a4',compress:true});
  readonly left = 16;
  readonly width = 178;
  readonly bottom = 274;
  y = 26;
  constructor(readonly reportId: string) { this.header(); }
  text(value: string, x: number, y: number, size = 9.5, bold = false, color = C.ink) {
    this.doc.setFont('helvetica', bold ? 'bold' : 'normal'); this.doc.setFontSize(size); this.doc.setTextColor(color);
    this.doc.text(value, x, y);
  }
  header() {
    this.doc.setFillColor(C.red); this.doc.rect(this.left,12,11,1.2,'F');
    this.text('GRAPHFIN', this.left+15,14,10,true);
    this.text('TRANSACTION NETWORK ANALYSIS',112,14,7.5,false,C.muted);
    this.doc.setDrawColor(C.line); this.doc.line(this.left,19,194,19);
  }
  nextPage() { this.doc.addPage(); this.y=28; this.header(); }
  ensure(height: number) { if(this.y+height>this.bottom)this.nextPage(); }
  section(number: number, title: string, subtitle?: string) {
    this.ensure(24); this.text(String(number).padStart(2,'0'),this.left,this.y+1,10,true,C.red);
    this.text(title,this.left+12,this.y+1,18,true); this.y+=12;
    if(subtitle)this.paragraph(subtitle,9.5,C.muted);
  }
  paragraph(value: string, size = 10, color = C.ink) {
    this.doc.setFont('helvetica','normal'); this.doc.setFontSize(size);
    const lines = this.doc.splitTextToSize(value,this.width) as string[];
    for(const line of lines){this.ensure(5);this.text(line,this.left,this.y,size,false,color);this.y+=size*0.46;}
    this.y+=3;
  }
  note(title: string, value: string) {
    this.doc.setFontSize(9);this.doc.setFont('helvetica','normal');
    const lines=this.doc.splitTextToSize(value,this.width-10) as string[];
    const height=13+lines.length*4.2;this.ensure(height+4);
    this.doc.setFillColor(C.pale);this.doc.rect(this.left,this.y,this.width,height,'F');
    this.doc.setFillColor(C.red);this.doc.rect(this.left,this.y,1,height,'F');
    this.text(title,this.left+5,this.y+6,9,true,C.red);
    lines.forEach((line,i)=>this.text(line,this.left+5,this.y+12+i*4.2,9));this.y+=height+5;
  }
  cards(items: {label:string;value:string;detail?:string}[], columns=3) {
    const gap=4,w=(this.width-gap*(columns-1))/columns;
    for(let i=0;i<items.length;i+=columns){this.ensure(32);
      items.slice(i,i+columns).forEach((item,j)=>{
        const x=this.left+j*(w+gap);this.doc.setFillColor(C.pale);this.doc.roundedRect(x,this.y,w,28,1.5,1.5,'F');
        this.text(item.label,x+4,this.y+6,8,false,C.muted);
        let size=16;this.doc.setFont('helvetica','bold');this.doc.setFontSize(size);
        while(this.doc.getTextWidth(item.value)>w-8&&size>9){size--;this.doc.setFontSize(size);}
        this.text(item.value,x+4,this.y+16,size,true,C.red);
        if(item.detail)this.text(item.detail,x+4,this.y+23,7.5,false,C.muted);
      });this.y+=32;
    }
    this.y+=2;
  }
  table(headers:string[], rows:string[][], widths:number[], size=9) {
    const lineHeight=size*0.43;
    const split=(value:string,width:number,bold=false)=>{
      this.doc.setFont('helvetica',bold?'bold':'normal');this.doc.setFontSize(size);
      const lines=this.doc.splitTextToSize(value,width-4) as string[];
      return lines.length>22?[...lines.slice(0,21),'[truncated]']:lines;
    };
    const headerLines=headers.map((h,i)=>split(h,widths[i],true));
    const hh=Math.max(...headerLines.map(l=>l.length))*lineHeight+5;
    const drawHeader=()=>{
      this.doc.setFillColor(C.ink);this.doc.rect(this.left,this.y,this.width,hh,'F');let x=this.left;
      headerLines.forEach((lines,i)=>{lines.forEach((l,j)=>this.text(l,x+2,this.y+4+j*lineHeight,size,true,C.white));x+=widths[i];});this.y+=hh;
    };
    this.ensure(hh+12);drawHeader();
    rows.forEach((row,index)=>{
      const cells=row.map((value,i)=>split(value,widths[i],i===0));
      const height=Math.max(...cells.map(l=>l.length))*lineHeight+5;
      if(this.y+height>this.bottom){this.nextPage();drawHeader();}
      if(index%2===0){this.doc.setFillColor(C.pale);this.doc.rect(this.left,this.y,this.width,height,'F');}
      let x=this.left;cells.forEach((lines,i)=>{lines.forEach((l,j)=>this.text(l,x+2,this.y+4+j*lineHeight,size,i===0));x+=widths[i];});this.y+=height;
    });this.y+=6;
  }
  bars(items:{label:string;value:number;unit:string}[]) {
    this.ensure(items.length*10+5);const max=Math.max(1,...items.map(i=>i.value));
    for(const item of items){this.text(item.label,this.left,this.y+3,9);this.doc.setFillColor(C.pale);this.doc.rect(87,this.y,72,4,'F');this.doc.setFillColor(C.red);this.doc.rect(87,this.y,72*item.value/max,4,'F');this.text(`${item.value} ${item.unit}`,162,this.y+3,8.5);this.y+=10;}this.y+=3;
  }
  finish() {
    const count=this.doc.getNumberOfPages();
    for(let p=1;p<=count;p++){this.doc.setPage(p);this.doc.setDrawColor(C.line);this.doc.line(this.left,281,194,281);this.text(this.reportId,this.left,286,7.5,false,C.muted);this.text('Research indicators - not proof of fraud',74,286,7.5,false,C.muted);this.text(`${p} / ${count}`,183,286,8,false,C.muted);}
    return this.doc;
  }
}
