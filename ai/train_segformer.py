"""Fine-tune SegFormer bằng ảnh và semantic mask PNG; chưa bao gồm dữ liệu.
python ai/train_segformer.py --data dataset --output ai/model --epochs 15
dataset/train.jsonl, val.jsonl: mỗi dòng {"image":"images/001.jpg","mask":"masks/001.png"}
Mask uint8: 0..5 là nhãn, 255 là vùng không gán. Không dùng ảnh mask màu RGB.
"""
import argparse
import json
from pathlib import Path
import random
import numpy as np
from PIL import Image, ImageOps
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoImageProcessor, AutoModelForSemanticSegmentation

LABELS={0:'background_unknown',1:'sidewalk',2:'roadway',3:'water_hazard',4:'stairs',5:'obstacle'}

class Samples(Dataset):
    def __init__(self,root,split,processor):
        self.root=root;self.processor=processor;self.training=split=='train'
        self.rows=[json.loads(s) for s in (root/(split+'.jsonl')).read_text(encoding='utf-8').splitlines() if s.strip()]
        if not self.rows: raise ValueError('Split không có mẫu: '+split)
    def __len__(self): return len(self.rows)
    def __getitem__(self,index):
        row=self.rows[index]
        with Image.open(self.root/row['image']) as im:image=im.convert('RGB')
        with Image.open(self.root/row['mask']) as im:
            if im.mode not in ('L','P'):raise ValueError('Mask phải PNG chỉ số nhãn 0..5/255, không phải RGB.')
            mask=Image.fromarray(np.array(im,dtype=np.uint8))
        values=set(np.unique(np.asarray(mask)).tolist())
        if not values<=set(LABELS)|{255}:raise ValueError('Mask chứa nhãn ngoài 0..5/255')
        if image.size!=mask.size:raise ValueError('Ảnh và mask khác kích thước')
        if self.training and random.random()<.5:image=ImageOps.mirror(image);mask=ImageOps.mirror(mask)
        out=self.processor(images=image,segmentation_maps=mask,return_tensors='pt')
        return {k:v.squeeze(0) for k,v in out.items()}

def evaluate(model,loader,device):
    model.eval();confusion=torch.zeros((6,6),device=device,dtype=torch.int64)
    with torch.inference_mode():
        for batch in loader:
            batch={k:v.to(device) for k,v in batch.items()}
            logits=model(pixel_values=batch['pixel_values']).logits
            predicted=torch.nn.functional.interpolate(logits,size=batch['labels'].shape[-2:],mode='bilinear',align_corners=False).argmax(1)
            truth=batch['labels'];valid=(truth>=0)&(truth<6)
            confusion+=torch.bincount(6*truth[valid]+predicted[valid],minlength=36).reshape(6,6)
    c=confusion.cpu().numpy();tp=np.diag(c);union=c.sum(0)+c.sum(1)-tp
    iou=np.divide(tp,union,out=np.full(6,np.nan),where=union>0)
    recalls=np.divide(tp,c.sum(1),out=np.full(6,np.nan),where=c.sum(1)>0)
    return {'miou':float(np.nanmean(iou)), 'iou':{LABELS[i]:None if np.isnan(v) else float(v) for i,v in enumerate(iou)},'recall':{LABELS[i]:None if np.isnan(v) else float(v) for i,v in enumerate(recalls)},'confusion_matrix':c.tolist()}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,required=True);parser.add_argument('--output',type=Path,default=Path('ai/model'));parser.add_argument('--epochs',type=int,default=15);parser.add_argument('--batch',type=int,default=2);parser.add_argument('--base',default='nvidia/segformer-b0-finetuned-ade-512-512');parser.add_argument('--eval-split',choices=['val','test'],default='val');parser.add_argument('--eval-only',action='store_true');args=parser.parse_args()
    random.seed(42);np.random.seed(42);torch.manual_seed(42)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    base=str(args.output) if args.eval_only else args.base
    processor=AutoImageProcessor.from_pretrained(base,do_reduce_labels=False,trust_remote_code=False)
    model=AutoModelForSemanticSegmentation.from_pretrained(base,num_labels=6,id2label=LABELS,label2id={v:k for k,v in LABELS.items()},ignore_mismatched_sizes=not args.eval_only,trust_remote_code=False,use_safetensors=True).to(device)
    validation=DataLoader(Samples(args.data,args.eval_split,processor),batch_size=args.batch,shuffle=False,num_workers=0)
    args.output.mkdir(parents=True,exist_ok=True)
    if args.eval_only:
        metrics=evaluate(model,validation,device);(args.output/('metrics-'+args.eval_split+'.json')).write_text(json.dumps(metrics,indent=2));print(json.dumps(metrics,indent=2));return
    if args.eval_split!='val':raise ValueError('Không dùng test để chọn checkpoint. Dùng --eval-only cho test.')
    training=DataLoader(Samples(args.data,'train',processor),batch_size=args.batch,shuffle=True,num_workers=0)
    optimizer=torch.optim.AdamW(model.parameters(),lr=5e-5,weight_decay=.01)
    best=-1;log=[]
    for epoch in range(args.epochs):
        model.train();loss_sum=0
        for batch in training:
            batch={k:v.to(device) for k,v in batch.items()};optimizer.zero_grad();loss=model(**batch).loss
            if not torch.isfinite(loss):raise RuntimeError('Loss không hữu hạn; kiểm tra mask (tránh toàn 255).')
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.0);optimizer.step();loss_sum+=loss.item()
        metrics=evaluate(model,validation,device);metrics.update(epoch=epoch+1,train_loss=loss_sum/len(training));log.append(metrics);print(json.dumps(metrics))
        if metrics['miou']>best:
            best=metrics['miou'];model.save_pretrained(args.output,safe_serialization=True);processor.save_pretrained(args.output)
        (args.output/'training-log.json').write_text(json.dumps(log,indent=2),encoding='utf-8')

if __name__=='__main__':main()
