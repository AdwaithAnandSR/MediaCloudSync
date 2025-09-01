import express from "express"
import cors from "cors"
import { config as dotenvConfig } from 'dotenv';


dotenvConfig();
const app = express()
const PORT = 5000;

app.use(express.json())
app.use(cors())
app.set('view engine', 'ejs')
app.use(express.static('public'))

import uploadFromVideo from "./controllers/video.controller.js"
import { getVideos } from "./store/video.store.js"

app.get("/", (req, res)=>{
    res.render("index", {title: "Media Cloud Sync", API: process.env.API })
})

app.get("/status", (req, res)=>{
    const videos = getVideos()
    
    res.json({ status: videos})
})



app.post("/processVideo", (req, res)=>{
    const { url } = req.body
    console.log("request recieved for url ", url)
    if(url) uploadFromVideo(url)
})

app.listen(PORT, ()=>{
    console.log("server started at port ", PORT)
})