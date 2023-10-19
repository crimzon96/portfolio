import React, { useState, useEffect } from "react";
import FeedBlock from "./FeedBlock";
import axios from "axios";
import getCookie from '../auth/Cookie';
var csrftoken = getCookie('csrftoken');
const Feed = ({ }) => {
    const [feedState, setFeedState] = useState({
        items: [],
        page: 0,
        hasMore: true


    })
    useEffect(() => {
        axios({
            headers:{
                'Authorization': localStorage.auth_token,
                'X-CSRFToken': csrftoken
            },
            method: 'get',
            url: "http://127.0.0.1:8000/api/feed/",
        })
            .then(function (response) {
                const feed_list = response.data.feed
                const big_feed_list = []
                while (feed_list.length > 0) {
                    big_feed_list.push(
                        feed_list.splice(0, 5)
                    )
                }
                setFeedState(oldstate => {
                    let paginated_results = {
                        ...oldstate,
                        items: big_feed_list[0],
                        all_items: big_feed_list

                    };
                    return paginated_results
                });

            })
            .catch(function (error) {
            });

    }, []);
    useEffect(() => {
        if (feedState.page > 0) {
            fetchData(feedState.page)
        }
    }, [feedState.page])

    const fetchData = (page) => {
        var newItems = []

        newItems = feedState.all_items[page]
        if (feedState.page > feedState.all_items.length) {
            setFeedState(oldstate => {
                let update_state = {
                    ...oldstate,
                    hasMore: false

                };
                return update_state
            });
        }
        if (feedState.page < feedState.all_items.length) {
            const mergeResult = feedState.items.concat(newItems)
            setFeedState(oldstate => ({ ...oldstate, items: mergeResult }))
        }
    }


    const onScroll = () => {
        const scrollTop = document.documentElement.scrollTop
        const scrollHeight = document.documentElement.scrollHeight
        const clientHeight = document.documentElement.clientHeight
        if (scrollTop + clientHeight + 500 >= scrollHeight && feedState.hasMore) {
            setFeedState(oldstate => {
                let update_state = {
                    ...oldstate,
                    page: feedState.page + 1

                };
                return update_state
            });
        }
    }
    useEffect(() => {
        window.addEventListener('scroll', onScroll)
        return () => window.removeEventListener('scroll', onScroll)
    }, [feedState.items])
    return (
        <>
            {feedState && feedState.items ?
                <>
                    {
                        feedState.items.map((
                            item, i) => (
                            <FeedBlock data={item} key={i}></FeedBlock>
                        )
                        )
                    }
                </>
                : null}

        </>
    )
}
export default Feed;
