const videos = []

export const addVideo = (id, url) => {
    const exist = videos.find(vid => vid.id === id);
    if (!exist) {
        videos.push({
            id,
            url,
            currentStatus: "processing...",
            status: "PROCESSING",
            type: "video"
        });
    }
};

export const getVideos = () => {
    return videos;
};

export const updateStatus = (id, updates)=>{
    const video = videos.find(vid=> vid.id === id)
    if(video){
        Object.assign(video, updates)
        console.log("\n\tupdated......", updates)
    }else{
        console.log("update video failed for id: ", id)
    }
}

export const generateId = () => {
  return Date.now().toString();
}

